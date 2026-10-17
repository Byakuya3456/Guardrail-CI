"""Deterministic path and size constraints for proposed remediation patches."""

from __future__ import annotations

from pathlib import PurePosixPath

from guardrail_ci.core.models import RemediationPlan

PROTECTED_PATHS: set[str] = {
    ".github/CODEOWNERS",
    ".github/branch-protection.yml",
    "SECURITY.md",
}

DENIED_PATH_PREFIXES: tuple[str, ...] = (
    ".git/",
    ".github/workflows/",
    ".github/actions/",
    "secrets/",
    ".env",
)

DENIED_FILE_NAMES: set[str] = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}

DENIED_EXTENSIONS: set[str] = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".crt",
    ".jks",
}

MAX_ALLOWED_FILES_PER_PATCH = 5


def is_path_allowed(path: str) -> tuple[bool, str]:
    """Check if a specific file path is permitted for modification."""
    normalized = PurePosixPath(path).as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized in PROTECTED_PATHS:
        return False, f"Path '{normalized}' is a protected security file."

    for prefix in DENIED_PATH_PREFIXES:
        if normalized.startswith(prefix) or f"/{prefix}" in f"/{normalized}":
            return False, f"Path '{normalized}' is in prohibited prefix '{prefix}'."

    file_name = PurePosixPath(normalized).name
    if file_name in DENIED_FILE_NAMES:
        return False, f"File name '{file_name}' may contain credentials and is blocked."

    suffix = PurePosixPath(normalized).suffix.lower()
    if suffix in DENIED_EXTENSIONS:
        return False, f"File extension '{suffix}' represents credentials and is blocked."

    return True, "Path is allowed."


def is_patch_allowed(plan: RemediationPlan, max_patch_size_bytes: int = 10000) -> tuple[bool, str]:
    """Evaluate full remediation plan against size, path, and file count constraints."""
    if not plan.files:
        return False, "Remediation plan contains no files to patch."

    if len(plan.files) > MAX_ALLOWED_FILES_PER_PATCH:
        return (
            False,
            f"Remediation modifies {len(plan.files)} files; exceeds maximum of {MAX_ALLOWED_FILES_PER_PATCH}.",
        )

    total_bytes = 0
    for patch_file in plan.files:
        allowed, reason = is_path_allowed(patch_file.path)
        if not allowed:
            return False, reason

        content_bytes = len(patch_file.modified_content.encode("utf-8"))
        diff_bytes = len(patch_file.diff.encode("utf-8"))
        total_bytes += max(content_bytes, diff_bytes)

        if total_bytes > max_patch_size_bytes:
            return (
                False,
                f"Patch payload ({total_bytes} bytes) exceeds maximum limit ({max_patch_size_bytes} bytes).",
            )

    return True, "Remediation patch satisfies all deterministic constraints."
