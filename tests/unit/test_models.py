"""Unit tests for domain models and state transitions."""

from __future__ import annotations

import pytest

from guardrail_ci.core.exceptions import InvalidStateTransitionError
from guardrail_ci.core.models import Incident, IncidentState


def test_incident_initial_state() -> None:
    incident = Incident(repository="owner/repo", run_id=123)
    assert incident.state == IncidentState.RECEIVED
    assert incident.incident_id is not None
    assert incident.diagnosis is None


def test_valid_state_transitions() -> None:
    incident = Incident(repository="owner/repo", run_id=123)
    incident.transition_to(IncidentState.EVIDENCE_COLLECTED)
    assert getattr(incident, "state") == IncidentState.EVIDENCE_COLLECTED

    incident.transition_to(IncidentState.DIAGNOSED)
    assert getattr(incident, "state") == IncidentState.DIAGNOSED

    incident.transition_to(IncidentState.COMPLETED_WITHOUT_WRITE)
    assert getattr(incident, "state") == IncidentState.COMPLETED_WITHOUT_WRITE


def test_invalid_state_transition_raises() -> None:
    incident = Incident(repository="owner/repo", run_id=123)
    # Skipping straight to PR_CREATED from RECEIVED is not allowed
    with pytest.raises(InvalidStateTransitionError):
        incident.transition_to(IncidentState.PR_CREATED)
