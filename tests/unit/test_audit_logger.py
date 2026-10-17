"""Unit tests for structured audit logger."""

from __future__ import annotations

import json
from pathlib import Path

from guardrail_ci.audit.logger import AuditLogger
from guardrail_ci.core.models import PolicyDecision


def test_audit_log_appends_and_redacts(tmp_path: Path) -> None:
    log_file = tmp_path / "test_audit.jsonl"
    audit = AuditLogger(str(log_file))

    decision = PolicyDecision(
        action="read_log",
        action_type="read",
        allowed=True,
        reason="Read is allowed",
    )

    # Details contain a secret token that must be redacted
    sensitive_details = {
        "repo": "owner/repo",
        "secret_token": "ghp_123456789012345678901234567890123456",
    }

    audit.log_decision(
        incident_id="test-incident-uuid",
        decision=decision,
        details=sensitive_details,
    )

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "ghp_" not in content
    assert "[REDACTED:github_classic_token]" in content

    parsed = json.loads(content.strip())
    assert parsed["incident_id"] == "test-incident-uuid"
    assert parsed["action"] == "read_log"
    assert parsed["allowed"] is True
