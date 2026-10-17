"""Unit tests for human approval gate, branch and pull request creation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.adapters.github.models import WorkflowRun
from guardrail_ci.cli.approval import request_approval
from guardrail_ci.config.settings import GitHubSettings
from guardrail_ci.core.models import (
    Diagnosis,
    FailureCategory,
    Incident,
    IncidentState,
    PatchFile,
    RemediationPlan,
)
from guardrail_ci.core.orchestrator import Orchestrator


def _create_mock_incident() -> Incident:
    return Incident(
        repository="owner/test-repo",
        run_id=500,
        state=IncidentState.VALIDATED,
        diagnosis=Diagnosis(
            failure_category=FailureCategory.UNIT_TEST,
            summary="Test assertion failed",
            likely_root_cause="Outdated fixture",
            confidence=0.85,
            recommended_actions=["Update fixture"],
        ),
        remediation_plan=RemediationPlan(
            description="Fix test fixture",
            intended_effect="Resolve assertion error",
            files=[
                PatchFile(
                    path="tests/fixture.json",
                    original_content='{"id": 1}',
                    modified_content='{"id": 2}',
                    diff="--- a/tests/fixture.json\n+++ b/tests/fixture.json\n@@ -1 +1 @@\n-{\"id\": 1}\n+{\"id\": 2}\n",
                )
            ],
            risks=["May alter test expectation"],
        ),
    )


def test_request_approval_user_confirms() -> None:
    incident = _create_mock_incident()
    with patch("click.confirm", return_value=True):
        result = request_approval(incident)
        assert result is True


def test_request_approval_user_declines() -> None:
    incident = _create_mock_incident()
    with patch("click.confirm", return_value=False):
        result = request_approval(incident)
        assert result is False


def test_publish_remediation_denied_when_unapproved(github_settings: GitHubSettings) -> None:
    incident = _create_mock_incident()
    mock_gh = MagicMock(spec=GitHubClient)

    orchestrator = Orchestrator(
        github_client=mock_gh,
        model_adapter=MagicMock(),
    )

    published = orchestrator.publish_remediation(incident, is_user_approved=False)
    assert published is False
    assert incident.approval_status == "denied"
    assert incident.state == IncidentState.COMPLETED_WITHOUT_WRITE

    # Verify no remote writes occurred
    mock_gh.create_branch.assert_not_called()
    mock_gh.create_pull_request.assert_not_called()


def test_publish_remediation_approved_creates_pr(github_settings: GitHubSettings) -> None:
    incident = _create_mock_incident()
    mock_gh = MagicMock(spec=GitHubClient)
    mock_gh.get_workflow_run.return_value = WorkflowRun(
        id=500,
        name="CI",
        head_branch="main",
        head_sha="abcdef123456",
        event="push",
        status="completed",
        conclusion="failure",
    )
    mock_gh.create_branch.return_value = {"ref": "refs/heads/guardrail-ci/fix-run-500"}
    mock_gh.create_or_update_file.return_value = {"content": "ok"}
    mock_gh.create_pull_request.return_value = {"html_url": "https://github.com/owner/test-repo/pull/1"}

    orchestrator = Orchestrator(
        github_client=mock_gh,
        model_adapter=MagicMock(),
    )

    published = orchestrator.publish_remediation(incident, is_user_approved=True)
    assert published is True
    assert incident.approval_status == "approved"
    assert incident.state == IncidentState.PR_CREATED

    mock_gh.create_branch.assert_called_once_with("owner/test-repo", "guardrail-ci/fix-run-500", "abcdef123456")
    mock_gh.create_or_update_file.assert_called_once()
    mock_gh.create_pull_request.assert_called_once()


def test_absence_of_merge_and_deploy_capabilities() -> None:
    """Negative security test: verify merge and deploy methods do not exist."""
    assert not hasattr(GitHubClient, "merge_pull_request")
    assert not hasattr(GitHubClient, "merge_pr")
    assert not hasattr(GitHubClient, "deploy")
    assert not hasattr(GitHubClient, "trigger_deployment")
    assert not hasattr(Orchestrator, "merge_pr")
    assert not hasattr(Orchestrator, "deploy")
