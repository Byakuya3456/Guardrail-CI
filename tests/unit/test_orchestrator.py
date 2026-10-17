"""Unit tests for the investigation orchestrator."""

from __future__ import annotations

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
    RemediationPlan,
)
from guardrail_ci.core.orchestrator import Orchestrator
from guardrail_ci.policy.engine import PolicyEngine


class MockModelAdapter(ModelAdapter):
    """Stub model adapter returning predictable diagnosis."""

    def diagnose(self, evidence: list[EvidenceItem], workflow_context: dict[str, Any]) -> Diagnosis:
        return Diagnosis(
            failure_category=FailureCategory.DEPENDENCY_INSTALLATION,
            summary="pip install failed to resolve requests package",
            evidence=evidence,
            likely_root_cause="Package requests==999.0.0 does not exist",
            confidence=0.92,
            recommended_actions=["Update requirements.txt to a valid requests version"],
        )

    def propose_remediation(self, diagnosis: Diagnosis, file_contents: dict[str, str]) -> RemediationPlan | None:
        return None


def test_orchestrator_investigate_success(github_settings: GitHubSettings, tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/actions/runs/101"):
            return httpx.Response(
                200,
                json={
                    "id": 101,
                    "name": "CI",
                    "event": "push",
                    "status": "completed",
                    "conclusion": "failure",
                },
            )
        if url.endswith("/actions/runs/101/jobs"):
            return httpx.Response(
                200,
                json={
                    "jobs": [
                        {
                            "id": 202,
                            "run_id": 101,
                            "name": "build",
                            "status": "completed",
                            "conclusion": "failure",
                            "steps": [
                                {
                                    "name": "Install dependencies",
                                    "status": "completed",
                                    "conclusion": "failure",
                                    "number": 2,
                                }
                            ],
                        }
                    ]
                },
            )
        if url.endswith("/actions/jobs/202/logs"):
            return httpx.Response(
                200,
                text="Step 2: Install dependencies\nERROR: Could not find a version that satisfies the requirement requests==999.0.0",
            )
        return httpx.Response(404)

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    github_client = GitHubClient(github_settings, http_client=mock_http)
    model_adapter = MockModelAdapter()
    audit_logger = AuditLogger(str(tmp_path / "audit.jsonl"))
    policy_engine = PolicyEngine()

    orchestrator = Orchestrator(
        github_client=github_client,
        model_adapter=model_adapter,
        policy_engine=policy_engine,
        audit_logger=audit_logger,
    )

    incident = orchestrator.investigate("owner/test-repo", 101)

    assert incident.state == IncidentState.COMPLETED_WITHOUT_WRITE
    assert incident.diagnosis is not None
    assert incident.diagnosis.failure_category == FailureCategory.DEPENDENCY_INSTALLATION
    assert incident.diagnosis.confidence == 0.92
    assert len(incident.evidence) == 1
    assert "requests==999.0.0" in incident.evidence[0].excerpt
    assert len(incident.policy_decisions) >= 3


def test_orchestrator_non_failure_run_fails(github_settings: GitHubSettings, tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": 102,
                "name": "CI",
                "event": "push",
                "status": "completed",
                "conclusion": "success",  # Not a failure!
            },
        )

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    github_client = GitHubClient(github_settings, http_client=mock_http)
    orchestrator = Orchestrator(
        github_client=github_client,
        model_adapter=MockModelAdapter(),
        audit_logger=AuditLogger(str(tmp_path / "audit.jsonl")),
    )

    incident = orchestrator.investigate("owner/test-repo", 102)
    assert incident.state == IncidentState.FAILED
    assert incident.error_message is not None and "expected 'failure'" in incident.error_message
