"""Deterministic policy evaluation engine enforcing security boundaries."""

from __future__ import annotations

from typing import Any

from guardrail_ci.core.models import PolicyDecision
from guardrail_ci.policy.actions import ActionType

PROHIBITED_ACTIONS: set[ActionType] = {
    ActionType.EXECUTE_SHELL,
    ActionType.MERGE,
    ActionType.DEPLOY,
    ActionType.MODIFY_SECURITY,
}

APPROVAL_REQUIRED: set[ActionType] = {
    ActionType.PUBLISH,
}

ALLOWED_ACTIONS: set[ActionType] = {
    ActionType.READ,
    ActionType.ANALYZE,
    ActionType.PREPARE_PATCH,
    ActionType.VALIDATE,
}


class PolicyEngine:
    """Evaluates requested tool actions against deterministic rules.

    The model CANNOT override policy.
    Default-deny for unrecognized action types or corrupted payloads.
    """

    def evaluate(
        self,
        action: str,
        action_type: str,
        context: dict[str, Any] | None = None,
        is_user_approved: bool = False,
    ) -> PolicyDecision:
        """Evaluate an action against security boundaries."""
        try:
            typed_action = ActionType(action_type)
        except ValueError:
            return PolicyDecision(
                action=action,
                action_type=action_type,
                allowed=False,
                reason=f"Unknown or unrecognized action type '{action_type}' — denied by default.",
            )

        if typed_action in PROHIBITED_ACTIONS:
            return PolicyDecision(
                action=action,
                action_type=typed_action.value,
                allowed=False,
                reason=f"Action '{action}' categorized as '{typed_action.value}' is strictly prohibited by security policy.",
            )

        if typed_action in APPROVAL_REQUIRED:
            if is_user_approved:
                return PolicyDecision(
                    action=action,
                    action_type=typed_action.value,
                    allowed=True,
                    requires_approval=True,
                    reason=f"Action '{action}' permitted after explicit human approval.",
                )
            return PolicyDecision(
                action=action,
                action_type=typed_action.value,
                allowed=False,
                requires_approval=True,
                reason=f"Action '{action}' requires explicit human review and approval before execution.",
            )

        if typed_action in ALLOWED_ACTIONS:
            return PolicyDecision(
                action=action,
                action_type=typed_action.value,
                allowed=True,
                reason=f"Action '{action}' of type '{typed_action.value}' is authorized by policy.",
            )

        return PolicyDecision(
            action=action,
            action_type=action_type,
            allowed=False,
            reason="Action fell through evaluation criteria — denied by default.",
        )
