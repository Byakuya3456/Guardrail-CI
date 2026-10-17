"""Unit tests for Orchestrator remediation and validation lifecycle."""

from pathlib import Path
from typing import Any

import httpx

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.audit.logger import AuditLogger
from guardrail_ci.config.settings import GitHubSettings
from guardrail_ci.core.models import (
    Diagnosis,
    EvidenceItem,
    FailureCategory,
    IncidentState,
    PatchFile,
    RemediationPlan,
    ValidationResult,
)
from guardrail_ci.core.orchestrator import Orchestrator
from guardrail_ci.storage.database import Database
from guardrail_ci.storage.repositories import IncidentRepository
from guardrail_ci.validation.worker import ValidationWorker


class MockWorker(ValidationWorker):
    """Stub validation worker for unit tests."""

    def __init__(self, should_pass: bool = True) -> None:
        self.should_pass = should_pass

    def run_check(self, command: str, workspace_path: Path) -> ValidationResult:
        return ValidationResult(
            command=command,
            exit_code=0 if self.should_pass else 1,
            stdout="Checks passed" if self.should_pass else "Assertion error",
            passed=self.should_pass,
            duration_seconds=0.1,
        )


class RemediationMockModel(ModelAdapter):
    """Model adapter proposing a valid patch."""

    def __init__(self, target_path: str = "requirements.txt") -> None:
        self.target_path = target_path

    def diagnose(self, evidence: list[EvidenceItem], workflow_context: dict[str, Any]) -> Diagnosis:
        return Diagnosis(
            failure_category=FailureCategory.DEPENDENCY_INSTALLATION,
            summary="Invalid dependency version",
            evidence=evidence,
            likely_root_cause="requests==999.0.0 does not exist",
            confidence=0.9,
            recommended_actions=["Pin requests to 2.31.0"],
        )

    def propose_remediation(self, diagnosis: Diagnosis, file_contents: dict[str, str]) -> RemediationPlan | None:
        return RemediationPlan(
            description="Fix dependency version",
            intended_effect="Resolve pip installation failure",
            files=[
                PatchFile(
                    path=self.target_path,
                    original_content="requests==999.0.0\n",
                    modified_content="requests==2.31.0\n",
                    diff="--- a/requirements.txt\n+++ b/requirements.txt\n@@ -1 +1 @@\n-requests==999.0.0\n+requests==2.31.0\n",
                )
            ],
        )


def _setup_mock_github(github_settings: GitHubSettings) -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/actions/runs/300" in url and "jobs" not in url:
            return httpx.Response(
                200,
                json={"id": 300, "name": "CI", "event": "push", "status": "completed", "conclusion": "failure"},
            )
        if "/actions/runs/300/jobs" in url:
            return httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 400,
                            "run_id": 300,
                            "name": "build",
                            "status": "completed",
                            "conclusion": "failure",
                            "steps": [{"name": "pip install", "status": "completed", "conclusion": "failure", "number": 1}],
                        }
                    ]
                },
            )
        if "/actions/jobs/400/logs" in url:
            return httpx.Response(200, text="ERROR: No matching distribution found for requests==999.0.0")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="https://api.github.com")
    return GitHubClient(github_settings, http_client=http_client)


def test_remediation_and_validation_success(github_settings: GitHubSettings, tmp_path: Path) -> None:
    github_client = _setup_mock_github(github_settings)
    db = Database(str(tmp_path / "test.db"))
    storage = IncidentRepository(db)
    audit = AuditLogger(str(tmp_path / "audit.jsonl"))

    orchestrator = Orchestrator(
        github_client=github_client,
        model_adapter=RemediationMockModel("requirements.txt"),
        audit_logger=audit,
        repository_storage=storage,
        validation_worker=MockWorker(should_pass=True),
    )

    incident = orchestrator.investigate(
        repo="owner/test-repo",
        run_id=300,
        propose_fix=True,
        candidate_files={"requirements.txt": "requests==999.0.0\n"},
        validation_commands=["pytest"],
    )

    assert incident.state == IncidentState.VALIDATED
    assert incident.remediation_plan is not None
    assert len(incident.validation_results) == 1
    assert incident.validation_results[0].passed is True

    # Verify persisted in SQLite database
    persisted = storage.get(incident.incident_id)
    assert persisted is not None
    assert persisted.state == IncidentState.VALIDATED


def test_remediation_rejected_on_protected_file(github_settings: GitHubSettings, tmp_path: Path) -> None:
    github_client = _setup_mock_github(github_settings)
    db = Database(str(tmp_path / "test.db"))
    storage = IncidentRepository(db)

    # Model attempts to modify a protected workflow file!
    malicious_model = RemediationMockModel(target_path=".github/workflows/ci.yml")

    orchestrator = Orchestrator(
        github_client=github_client,
        model_adapter=malicious_model,
        audit_logger=AuditLogger(str(tmp_path / "audit.jsonl")),
        repository_storage=storage,
        validation_worker=MockWorker(should_pass=True),
    )

    incident = orchestrator.investigate(
        repo="owner/test-repo",
        run_id=300,
        propose_fix=True,
        candidate_files={".github/workflows/ci.yml": "name: CI\n"},
        validation_commands=["pytest"],
    )

    # Must NOT reach VALIDATED because constraints rejected the workflow path
    assert incident.state == IncidentState.COMPLETED_WITHOUT_WRITE
