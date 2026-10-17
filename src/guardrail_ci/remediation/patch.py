"""Diff generation and workspace patch application."""

from __future__ import annotations

import difflib
from pathlib import Path

from guardrail_ci.core.models import RemediationPlan


def generate_unified_diff(
    path: str,
    original_content: str | None,
    modified_content: str,
) -> str:
    """Generate a standard unified diff between original and modified text."""
    orig_lines = (original_content or "").splitlines(keepends=True)
    mod_lines = modified_content.splitlines(keepends=True)

    diff_lines = list(
        difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )
    return "".join(diff_lines)


def apply_patch_to_workspace(workspace_dir: Path, plan: RemediationPlan) -> list[str]:
    """Write modified files from a validated RemediationPlan into a workspace directory."""
    modified_paths: list[str] = []
    resolved_workspace = workspace_dir.resolve()

    for patch_file in plan.files:
        cleaned_rel_path = patch_file.path.strip().lstrip("/\\")
        target_path = (workspace_dir / cleaned_rel_path).resolve()

        if not target_path.is_relative_to(resolved_workspace):
            raise ValueError(
                f"Path traversal security violation: '{patch_file.path}' escapes workspace directory."
            )

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(patch_file.modified_content, encoding="utf-8")
        modified_paths.append(patch_file.path)
    return modified_paths
