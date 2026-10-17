"""Unit tests for the CLI interface."""

from __future__ import annotations

from unittest.mock import patch

from click.testing import CliRunner

from guardrail_ci.cli.main import cli
from guardrail_ci.core.models import (
    Diagnosis,
    EvidenceItem,
    FailureCategory,
    Incident,
    IncidentState,
    PolicyDecision,
)


def test_cli_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_cli_investigate_json_output() -> None:
    mock_incident = Incident(
        repository="owner/test-repo",
        run_id=12345,
        state=IncidentState.COMPLETED_WITHOUT_WRITE,
        evidence=[
            EvidenceItem(
                job="build",
                step="test",
                excerpt="Failed test",
                source="job:1/step:1",
            )
        ],
        diagnosis=Diagnosis(
            failure_category=FailureCategory.UNIT_TEST,
            summary="Unit test assertion failure",
            evidence=[],
            likely_root_cause="Bad assertion on line 12",
            confidence=0.88,
            recommended_actions=["Fix test assertion"],
        ),
        policy_decisions=[
            PolicyDecision(
                action="get_workflow_run",
                action_type="read",
                allowed=True,
                reason="Read is authorized",
            )
        ],
    )

    with patch("guardrail_ci.core.orchestrator.Orchestrator.investigate", return_value=mock_incident):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["investigate", "--repo", "owner/test-repo", "--run-id", "12345", "--output", "json"],
        )
        assert result.exit_code == 0
        assert '"repository": "owner/test-repo"' in result.output
        assert '"failure_category": "unit_test"' in result.output


def test_cli_investigate_rich_output() -> None:
    mock_incident = Incident(
        repository="owner/test-repo",
        run_id=12345,
        state=IncidentState.COMPLETED_WITHOUT_WRITE,
        diagnosis=Diagnosis(
            failure_category=FailureCategory.LINT_TYPE_CHECK,
            summary="Ruff detected unused imports",
            evidence=[
                EvidenceItem(
                    job="lint",
                    step="run ruff",
                    excerpt="F401 'os' imported but unused",
                )
            ],
            likely_root_cause="Unused import",
            confidence=0.95,
            recommended_actions=["Remove unused import"],
        ),
    )

    with patch("guardrail_ci.core.orchestrator.Orchestrator.investigate", return_value=mock_incident):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["investigate", "--repo", "owner/test-repo", "--run-id", "12345", "--output", "rich"],
        )
        assert result.exit_code == 0
        assert "Guardrail-CI Incident Report" in result.output
        assert "lint_type_check" in result.output
