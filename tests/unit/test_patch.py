"""Unit tests for diff generation and workspace patch application."""

from __future__ import annotations

from pathlib import Path

from guardrail_ci.core.models import PatchFile, RemediationPlan
from guardrail_ci.remediation.patch import apply_patch_to_workspace, generate_unified_diff


def test_generate_unified_diff() -> None:
    original = "line1\nline2\nline3\n"
    modified = "line1\nline2_modified\nline3\n"

    diff = generate_unified_diff("src/test.txt", original, modified)
    assert "--- a/src/test.txt" in diff
    assert "+++ b/src/test.txt" in diff
    assert "-line2" in diff
    assert "+line2_modified" in diff


def test_apply_patch_to_workspace(tmp_path: Path) -> None:
    plan = RemediationPlan(
        description="Fix import",
        intended_effect="Resolve import error",
        files=[
            PatchFile(
                path="src/pkg/module.py",
                original_content="# empty",
                modified_content="import sys\n",
                diff="...",
            )
        ],
    )

    applied = apply_patch_to_workspace(tmp_path, plan)
    assert applied == ["src/pkg/module.py"]

    written_file = tmp_path / "src" / "pkg" / "module.py"
    assert written_file.exists()
    assert written_file.read_text(encoding="utf-8") == "import sys\n"
