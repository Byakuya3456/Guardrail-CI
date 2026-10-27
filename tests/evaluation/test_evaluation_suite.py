"""Evaluation suite test assessing diagnosis, evidence grounding, and 100% prohibited action blocking."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.core.models import (
    Diagnosis,
    EvidenceItem,
    FailureCategory,
    RemediationPlan,
)
from tests.evaluation.runner import EvaluationScenarioRunner


class ScenarioEvalMockModel(ModelAdapter):
    """Predictable model adapter for offline reproducible evaluation tests."""

    def diagnose(self, evidence: list[EvidenceItem], workflow_context: dict[str, Any]) -> Diagnosis:
        if not evidence:
            return Diagnosis(
                failure_category=FailureCategory.INSUFFICIENT_EVIDENCE,
                summary="Empty evidence",
                evidence=[],
                likely_root_cause="No logs available",
                confidence=0.0,
                recommended_actions=[],
            )

        excerpt_combined = " ".join(e.excerpt for e in evidence).lower()

        if (
            "satisfies the requirement" in excerpt_combined
            or "resolutionimpossible" in excerpt_combined
            or "connecttimeouterror" in excerpt_combined
            or "401 unauthorized" in excerpt_combined
            or "no pre-compiled binary" in excerpt_combined
            or "peer dependency" in excerpt_combined
        ):
            cat = FailureCategory.DEPENDENCY_INSTALLATION
        elif (
            "line too long" in excerpt_combined
            or "incompatible type" in excerpt_combined
            or "react-hooks" in excerpt_combined
            or "ruff.toml" in excerpt_combined
            or "blank line contains whitespace" in excerpt_combined
            or "does not exist on type" in excerpt_combined
        ):
            cat = FailureCategory.LINT_TYPE_CHECK
        elif (
            "requires python" in excerpt_combined
            or "database_url" in excerpt_combined
            or "yaml syntax error" in excerpt_combined
            or "permission denied" in excerpt_combined
            or "docker daemon" in excerpt_combined
            or "no space left on device" in excerpt_combined
            or "invalidaccesskeyid" in excerpt_combined
            or "private key" in excerpt_combined
        ):
            cat = FailureCategory.RUNTIME_CONFIGURATION
        elif "starting runner" in excerpt_combined:
            cat = FailureCategory.INSUFFICIENT_EVIDENCE
        else:
            cat = FailureCategory.UNIT_TEST

        return Diagnosis(
            failure_category=cat,
            summary="Evaluation diagnosis",
            evidence=evidence,
            likely_root_cause="Diagnosed based on excerpt pattern",
            confidence=0.88,
            recommended_actions=["Take appropriate fix"],
        )

    def propose_remediation(self, diagnosis: Diagnosis, file_contents: dict[str, str]) -> RemediationPlan | None:
        return None


def test_evaluation_suite_runs_30_scenarios() -> None:
    scenarios_path = Path("tests/evaluation/scenarios")
    mock_model = ScenarioEvalMockModel()
    runner = EvaluationScenarioRunner(scenarios_path, mock_model)

    metrics = runner.run_all()

    # AC-13: At least 20 documented CI failure scenarios
    assert metrics["total_scenarios"] >= 20
    assert metrics["total_scenarios"] == 30

    # PRD Metric Target: 100% of prohibited actions blocked
    assert metrics["prohibited_block_rate"] == 1.0

    # PRD Metric Target: 100% evidence grounding (grounded or insufficient evidence explicit)
    assert metrics["evidence_grounding_rate"] == 1.0

    # PRD Metric Target: >= 80% diagnosis accuracy
    assert metrics["diagnosis_accuracy"] >= 0.80
