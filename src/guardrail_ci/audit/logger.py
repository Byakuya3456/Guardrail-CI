"""Structured JSONL audit logger with automated credential redaction."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from guardrail_ci.core.models import PolicyDecision
from guardrail_ci.evidence.redactor import redact_secrets

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only structured audit logger for tracking all operations and policy checks."""

    def __init__(self, log_path: str = "./audit.jsonl") -> None:
        self._path = Path(log_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log_decision(self, incident_id: str, decision: PolicyDecision, details: dict[str, Any] | None = None) -> None:
        """Record a policy decision with sanitized details."""
        self.log_action(
            incident_id=incident_id,
            action=decision.action,
            action_type=decision.action_type,
            allowed=decision.allowed,
            reason=decision.reason,
            details=details,
        )

    def log_action(
        self,
        incident_id: str,
        action: str,
        action_type: str,
        allowed: bool,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Write an immutable audit log entry."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "incident_id": incident_id,
            "action": action,
            "action_type": action_type,
            "allowed": allowed,
            "reason": reason,
        }

        if details is not None:
            raw_details = json.dumps(details, default=str)
            sanitized_details = redact_secrets(raw_details)
            entry["details"] = json.loads(sanitized_details)

        line = json.dumps(entry, default=str)
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            logger.error("Failed writing to audit log %s: %s", self._path, e)
