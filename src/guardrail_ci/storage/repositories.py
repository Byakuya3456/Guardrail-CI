"""Incident repository for SQLite persistence."""

from __future__ import annotations

import json
from typing import Any

from guardrail_ci.core.models import Incident
from guardrail_ci.storage.database import Database


class IncidentRepository:
    """Data access repository for Incident entities."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def save(self, incident: Incident) -> None:
        """Insert or update an incident record."""
        payload = incident.model_dump_json()
        with self._db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO incidents (incident_id, repository, run_id, state, created_at, updated_at, data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    state = excluded.state,
                    updated_at = excluded.updated_at,
                    data = excluded.data;
                """,
                (
                    incident.incident_id,
                    incident.repository,
                    incident.run_id,
                    incident.state.value,
                    incident.created_at.isoformat(),
                    incident.updated_at.isoformat(),
                    payload,
                ),
            )

    def get(self, incident_id: str) -> Incident | None:
        """Retrieve an incident by primary key identifier."""
        with self._db.get_connection() as conn:
            row = conn.execute(
                "SELECT data FROM incidents WHERE incident_id = ?;",
                (incident_id,),
            ).fetchone()
            if not row:
                return None
            data: dict[str, Any] = json.loads(row["data"])
            return Incident.model_validate(data)

    def find_by_repo_and_run(self, repo: str, run_id: int) -> list[Incident]:
        """Find incidents matching a given repository and run identifier."""
        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT data FROM incidents WHERE repository = ? AND run_id = ? ORDER BY created_at DESC;",
                (repo, run_id),
            ).fetchall()
            return [Incident.model_validate(json.loads(r["data"])) for r in rows]

    def list_all(self, limit: int = 50) -> list[Incident]:
        """List recently created incidents."""
        with self._db.get_connection() as conn:
            rows = conn.execute(
                "SELECT data FROM incidents ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
            return [Incident.model_validate(json.loads(r["data"])) for r in rows]
