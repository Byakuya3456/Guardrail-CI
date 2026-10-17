"""Automated evaluation suite runner for reproducing and assessing CI failure scenarios."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from guardrail_ci.adapters.model.base import ModelAdapter
from guardrail_ci.core.models import EvidenceItem
from guardrail_ci.policy.engine import PolicyEngine


class EvaluationScenarioRunner:
    """Runs documented CI failure scenarios against the model adapter and policy engine."""

    def __init__(self, scenarios_dir: Path, model_adapter: ModelAdapter) -> None:
        self.scenarios_dir = scenarios_dir
        self.model = model_adapter
        self.policy = PolicyEngine()
        self.scenarios = self._load_scenarios()

    def _load_scenarios(self) -> list[dict[str, Any]]:
        """Load all scenario JSON definition files."""
        scenarios: list[dict[str, Any]] = []
        if not self.scenarios_dir.exists():
            return scenarios

        for json_file in sorted(self.scenarios_dir.glob("*.json")):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                scenarios.append(data)
            except json.JSONDecodeError:
                continue
        return scenarios

    def evaluate_scenario(self, scenario: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single scenario for diagnosis accuracy, evidence grounding, and policy blocking."""
        # 1. Evaluate Diagnosis
        evidence_data = scenario.get("evidence", [])
        evidence_items = [
            EvidenceItem(
                job=e.get("job", "build"),
                step=e.get("step", "step"),
                excerpt=e.get("excerpt", ""),
                source=e.get("source", "log"),
            )
            for e in evidence_data
        ]

        diagnosis = self.model.diagnose(
            evidence=evidence_items,
            workflow_context={"repository": "evaluation/repo", "run_id": 9999},
        )

        expected_cat = scenario.get("expected_failure_category")
        diagnosis_correct = (
            expected_cat is None or diagnosis.failure_category.value == expected_cat
        )

        has_evidence = len(diagnosis.evidence) > 0 or diagnosis.failure_category.value == "insufficient_evidence"

        # 2. Evaluate Prohibited Action Blocking
        prohibited_tested = 0
        prohibited_blocked = 0
        for action_name, action_type in scenario.get("prohibited_actions_to_test", []):
            decision = self.policy.evaluate(action=action_name, action_type=action_type)
            prohibited_tested += 1
            if not decision.allowed:
                prohibited_blocked += 1

        return {
            "scenario_id": scenario.get("scenario_id", "unknown"),
            "diagnosis_correct": diagnosis_correct,
            "evidence_grounded": has_evidence,
            "confidence": diagnosis.confidence,
            "prohibited_tested": prohibited_tested,
            "prohibited_blocked": prohibited_blocked,
        }

    def run_all(self) -> dict[str, Any]:
        """Execute all scenarios and calculate aggregate evaluation metrics."""
        results: list[dict[str, Any]] = []
        total = len(self.scenarios)

        correct_count = 0
        grounded_count = 0
        total_prohibited_tested = 0
        total_prohibited_blocked = 0

        for sc in self.scenarios:
            res = self.evaluate_scenario(sc)
            results.append(res)
            if res["diagnosis_correct"]:
                correct_count += 1
            if res["evidence_grounded"]:
                grounded_count += 1
            total_prohibited_tested += res["prohibited_tested"]
            total_prohibited_blocked += res["prohibited_blocked"]

        accuracy = correct_count / total if total > 0 else 0.0
        grounding = grounded_count / total if total > 0 else 0.0
        block_rate = (
            total_prohibited_blocked / total_prohibited_tested
            if total_prohibited_tested > 0
            else 1.0
        )

        return {
            "total_scenarios": total,
            "diagnosis_accuracy": accuracy,
            "evidence_grounding_rate": grounding,
            "prohibited_block_rate": block_rate,
            "scenario_results": results,
        }
