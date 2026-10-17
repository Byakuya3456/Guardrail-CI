"""Unit tests for deterministic policy engine."""

from __future__ import annotations

from guardrail_ci.policy.actions import ActionType
from guardrail_ci.policy.engine import PolicyEngine


def test_allowed_actions_pass() -> None:
    engine = PolicyEngine()
    for act_type in [ActionType.READ, ActionType.ANALYZE, ActionType.PREPARE_PATCH, ActionType.VALIDATE]:
        decision = engine.evaluate(action=f"do_{act_type.value}", action_type=act_type.value)
        assert decision.allowed is True
        assert "authorized" in decision.reason.lower() or "permitted" in decision.reason.lower()


def test_prohibited_actions_blocked() -> None:
    engine = PolicyEngine()
    prohibited = [
        ("run_bash", ActionType.EXECUTE_SHELL.value),
        ("auto_merge", ActionType.MERGE.value),
        ("deploy_prod", ActionType.DEPLOY.value),
        ("disable_scanner", ActionType.MODIFY_SECURITY.value),
    ]
    for action_name, action_type in prohibited:
        decision = engine.evaluate(action=action_name, action_type=action_type)
        assert decision.allowed is False
        assert "prohibited" in decision.reason.lower()


def test_unknown_action_denied_by_default() -> None:
    engine = PolicyEngine()
    decision = engine.evaluate(action="mystery_op", action_type="non_existent_type")
    assert decision.allowed is False
    assert "denied by default" in decision.reason.lower()


def test_publish_action_requires_approval() -> None:
    engine = PolicyEngine()
    # Unapproved -> Denied
    decision = engine.evaluate(action="create_pr", action_type=ActionType.PUBLISH.value, is_user_approved=False)
    assert decision.allowed is False
    assert decision.requires_approval is True

    # User Approved -> Allowed
    approved_decision = engine.evaluate(action="create_pr", action_type=ActionType.PUBLISH.value, is_user_approved=True)
    assert approved_decision.allowed is True
    assert approved_decision.requires_approval is True
