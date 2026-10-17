"""Incident lifecycle states and valid transition rules."""

from __future__ import annotations

from enum import Enum


class IncidentState(str, Enum):
    """Incident lifecycle states."""

    RECEIVED = "received"
    EVIDENCE_COLLECTED = "evidence_collected"
    DIAGNOSED = "diagnosed"
    PLAN_PROPOSED = "plan_proposed"
    POLICY_CHECKED = "policy_checked"
    PATCH_PREPARED = "patch_prepared"
    VALIDATING = "validating"
    VALIDATED = "validated"
    VALIDATION_FAILED = "validation_failed"
    AWAITING_APPROVAL = "awaiting_approval"
    PR_CREATED = "pr_created"
    COMPLETED_WITHOUT_WRITE = "completed_without_write"
    FAILED = "failed"


VALID_TRANSITIONS: dict[IncidentState, set[IncidentState]] = {
    IncidentState.RECEIVED: {
        IncidentState.EVIDENCE_COLLECTED,
        IncidentState.FAILED,
    },
    IncidentState.EVIDENCE_COLLECTED: {
        IncidentState.DIAGNOSED,
        IncidentState.FAILED,
    },
    IncidentState.DIAGNOSED: {
        IncidentState.PLAN_PROPOSED,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.PLAN_PROPOSED: {
        IncidentState.POLICY_CHECKED,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.POLICY_CHECKED: {
        IncidentState.PATCH_PREPARED,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.PATCH_PREPARED: {
        IncidentState.VALIDATING,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.VALIDATING: {
        IncidentState.VALIDATED,
        IncidentState.VALIDATION_FAILED,
        IncidentState.FAILED,
    },
    IncidentState.VALIDATED: {
        IncidentState.AWAITING_APPROVAL,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.VALIDATION_FAILED: {
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.AWAITING_APPROVAL: {
        IncidentState.PR_CREATED,
        IncidentState.COMPLETED_WITHOUT_WRITE,
        IncidentState.FAILED,
    },
    IncidentState.PR_CREATED: set(),
    IncidentState.COMPLETED_WITHOUT_WRITE: set(),
    IncidentState.FAILED: set(),
}


def can_transition(current: IncidentState, target: IncidentState) -> bool:
    """Verify if a state transition is permitted."""
    return target in VALID_TRANSITIONS.get(current, set())
