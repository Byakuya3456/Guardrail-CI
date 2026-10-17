"""Unit tests for remediation patch constraints."""

from __future__ import annotations

from guardrail_ci.core.models import PatchFile, RemediationPlan
from guardrail_ci.remediation.constraints import is_patch_allowed, is_path_allowed


def test_allowed_paths() -> None:
    allowed_paths = [
        "src/app/main.py",
        "requirements.txt",
        "pyproject.toml",
        "package.json",
        "tests/unit/test_something.py",
    ]
    for path in allowed_paths:
        allowed, reason = is_path_allowed(path)
        assert allowed is True, f"Expected {path} to be allowed, got: {reason}"


def test_denied_paths_and_prefixes() -> None:
    denied = [
        ".github/workflows/ci.yml",
        ".github/actions/setup/action.yml",
        ".git/config",
        "secrets/prod_key.json",
        ".env",
        ".env.local",
        "id_rsa",
        "cert.pem",
        "private.key",
        "../../etc/passwd",
        "../outside.py",
        "/etc/shadow",
        "C:/Windows/system.ini",
        "src/../../evil.py",
        "\\\\evil\\share\\file.py",
    ]
    for path in denied:
        allowed, reason = is_path_allowed(path)
        assert allowed is False, f"Expected {path} to be denied"
        assert len(reason) > 0


def test_patch_size_constraint_enforced() -> None:
    huge_content = "x" * 15000
    plan = RemediationPlan(
        description="Huge patch",
        intended_effect="Exceeds limit",
        files=[
            PatchFile(
                path="src/file.py",
                modified_content=huge_content,
                diff=huge_content,
            )
        ],
    )
    allowed, reason = is_patch_allowed(plan, max_patch_size_bytes=10000)
    assert allowed is False
    assert "exceeds maximum limit" in reason


def test_patch_file_count_constraint() -> None:
    files = [
        PatchFile(
            path=f"src/file_{i}.py",
            modified_content="print(1)",
            diff="+print(1)",
        )
        for i in range(7)
    ]
    plan = RemediationPlan(
        description="Too many files",
        intended_effect="Affects too much code",
        files=files,
    )
    allowed, reason = is_patch_allowed(plan)
    assert allowed is False
    assert "exceeds maximum of 5" in reason
