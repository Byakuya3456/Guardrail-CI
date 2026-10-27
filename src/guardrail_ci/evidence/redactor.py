"""Secret and credential redaction for logs, evidence, and prompts."""

from __future__ import annotations

import re

# Deterministic regex patterns that indicate sensitive credentials
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("github_classic_token", re.compile(r"ghp_[A-Za-z0-9]{30,45}", re.ASCII)),
    ("github_fine_grained_token", re.compile(r"github_pat_[A-Za-z0-9_]{82}", re.ASCII)),
    ("github_app_token", re.compile(r"gh[soru]_[A-Za-z0-9]{36,255}", re.ASCII)),
    ("aws_access_key", re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b", re.ASCII)),
    ("aws_secret_key", re.compile(r"(?i)(aws_secret_access_key|aws_secret|secret_key)\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?", re.ASCII)),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*", re.ASCII)),
    ("generic_api_key", re.compile(r"(?i)(api[_-]?key|apikey|auth_token)\s*[:=]\s*['\"]?([A-Za-z0-9\-_]{16,})['\"]?", re.ASCII)),
    ("generic_password", re.compile(r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{6,})['\"]?", re.ASCII)),
    ("private_key_header", re.compile(r"-----BEGIN\s+([A-Z0-9_\s]+)?PRIVATE KEY-----[\s\S]*?-----END\s+([A-Z0-9_\s]+)?PRIVATE KEY-----", re.ASCII)),
]


def redact_secrets(text: str) -> str:
    """Replace recognized secret-like patterns with [REDACTED:token_type]."""
    if not text:
        return ""
    result = text
    for name, pattern in SECRET_PATTERNS:
        result = pattern.sub(f"[REDACTED:{name}]", result)
    return result


def is_potentially_sensitive(text: str) -> bool:
    """Return True if text matches any credential or secret pattern."""
    if not text:
        return False
    return any(pattern.search(text) is not None for _, pattern in SECRET_PATTERNS)
