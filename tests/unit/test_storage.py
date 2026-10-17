"""Unit tests for SQLite storage layer and IncidentRepository."""

from __future__ import annotations

from guardrail_ci.core.models import (
    Diagnosis,
    EvidenceItem,
    FailureCategory,
    Incident,
    IncidentState,
    PolicyDecision,
)
from guardrail_ci.storage.database import Database
from guardrail_ci.storage.repositories import IncidentRepository


def test_database_initialization_in_memory() -> None:
    db = Database(":memory:")
    with db.get_connection() as conn:
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='incidents';"
        ).fetchall()
        assert len(tables) == 1


def test_incident_repository_save_and_get() -> None:
    db = Database(":memory:")
    repo = IncidentRepository(db)

    incident = Incident(
        repository="owner/test-repo",
        run_id=456,
        state=IncidentState.DIAGNOSED,
        evidence=[
            EvidenceItem(
                job="test",
                step="pytest",
                excerpt="Failure",
                source="job:1/step:1",
            )
        ],
        diagnosis=Diagnosis(
            failure_category=FailureCategory.UNIT_TEST,
            summary="Unit test failed",
            evidence=[],
            likely_root_cause="Bad test",
            confidence=0.8,
            recommended_actions=["Fix test"],
        ),
        policy_decisions=[
            PolicyDecision(
                action="read",
                action_type="read",
                allowed=True,
                reason="Permitted",
            )
        ],
    )

    repo.save(incident)

    retrieved = repo.get(incident.incident_id)
    assert retrieved is not None
    assert retrieved.incident_id == incident.incident_id
    assert retrieved.repository == "owner/test-repo"
    assert retrieved.run_id == 456
    assert retrieved.state == IncidentState.DIAGNOSED
    assert retrieved.diagnosis is not None
    assert retrieved.diagnosis.failure_category == FailureCategory.UNIT_TEST


def test_incident_repository_upsert_update() -> None:
    db = Database(":memory:")
    repo = IncidentRepository(db)

    incident = Incident(repository="owner/repo", run_id=101)
    repo.save(incident)

    # Update state
    incident.transition_to(IncidentState.EVIDENCE_COLLECTED)
    repo.save(incident)

    updated = repo.get(incident.incident_id)
    assert updated is not None
    assert updated.state == IncidentState.EVIDENCE_COLLECTED


def test_incident_repository_find_and_list() -> None:
    db = Database(":memory:")
    repo = IncidentRepository(db)

    inc1 = Incident(repository="owner/repo", run_id=100)
    inc2 = Incident(repository="owner/repo", run_id=100)
    inc3 = Incident(repository="other/repo", run_id=200)

    repo.save(inc1)
    repo.save(inc2)
    repo.save(inc3)

    found = repo.find_by_repo_and_run("owner/repo", 100)
    assert len(found) == 2

    all_incidents = repo.list_all()
    assert len(all_incidents) == 3
