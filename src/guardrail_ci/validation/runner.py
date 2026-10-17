"""Validation runner coordinating patch application and verification checks."""

from __future__ import annotations

import tempfile
from pathlib import Path

from guardrail_ci.core.models import RemediationPlan, ValidationResult
from guardrail_ci.remediation.patch import apply_patch_to_workspace
from guardrail_ci.validation.worker import ValidationWorker


class ValidationRunner:
    """Coordinates isolated testing of proposed remediation patches."""

    def __init__(self, worker: ValidationWorker) -> None:
        self._worker = worker

    def validate_plan(
        self,
        plan: RemediationPlan,
        commands: list[str],
        base_dir: Path | None = None,
    ) -> tuple[bool, list[ValidationResult]]:
        """Apply patch to a temporary disposable workspace and execute checks."""
        results: list[ValidationResult] = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            workspace_path = Path(tmp_dir)

            # Copy base repository if provided
            if base_dir and base_dir.exists():
                import shutil
                for item in base_dir.iterdir():
                    if item.name == ".git":
                        continue
                    dest = workspace_path / item.name
                    if item.is_dir():
                        shutil.copytree(item, dest)
                    else:
                        shutil.copy2(item, dest)

            # Apply proposed patch to the disposable workspace
            apply_patch_to_workspace(workspace_path, plan)

            # Execute each allowlisted command sequentially
            for cmd in commands:
                result = self._worker.run_check(cmd, workspace_path)
                results.append(result)
                if not result.passed:
                    # Fail fast if any required check fails
                    return False, results

        all_passed = len(results) > 0 and all(r.passed for r in results)
        return all_passed, results
