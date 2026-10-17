"""Unit tests for secret redaction engine."""

from __future__ import annotations

from guardrail_ci.evidence.redactor import is_potentially_sensitive, redact_secrets


def test_redact_github_classic_token() -> None:
    text = "Error: request failed with Authorization: token ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    redacted = redact_secrets(text)
    assert "ghp_" not in redacted
    assert "[REDACTED:github_classic_token]" in redacted


def test_redact_github_fine_grained_token() -> None:
    token = "github_pat_" + "A" * 82
    text = f"Using token {token} for repository checkout"
    redacted = redact_secrets(text)
    assert "github_pat_" not in redacted
    assert "[REDACTED:github_fine_grained_token]" in redacted


def test_redact_aws_access_key() -> None:
    text = "AWS credentials failed for AKIAIOSFODNN7EXAMPLE in us-east-1"
    redacted = redact_secrets(text)
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted
    assert "[REDACTED:aws_access_key]" in redacted


def test_redact_bearer_token() -> None:
    text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
    redacted = redact_secrets(text)
    assert "Bearer eyJhbG" not in redacted
    assert "[REDACTED:bearer_token]" in redacted


def test_redact_api_key_assignment() -> None:
    text = "api_key = 'sk-1234567890abcdef1234567890'"
    redacted = redact_secrets(text)
    assert "sk-1234567890" not in redacted
    assert "[REDACTED:generic_api_key]" in redacted


def test_clean_text_unaltered() -> None:
    clean_text = "Step completed: pytest tests/unit/ -v --exitfirst"
    assert redact_secrets(clean_text) == clean_text
    assert not is_potentially_sensitive(clean_text)


def test_is_potentially_sensitive() -> None:
    assert is_potentially_sensitive("ghp_123456789012345678901234567890123456")
    assert not is_potentially_sensitive("Compilation finished with 0 errors.")
