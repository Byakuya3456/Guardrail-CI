"""SQLite database management and schema migrations."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    """Manages SQLite database connections and table creation."""

    def __init__(self, db_path: str = "./guardrail_ci.db") -> None:
        self.db_path = db_path
        self._memory_conn: sqlite3.Connection | None = None

        if db_path == ":memory:":
            self._memory_conn = sqlite3.connect(":memory:")
            self._memory_conn.row_factory = sqlite3.Row
            self._memory_conn.execute("PRAGMA foreign_keys = ON;")
        else:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.initialize_schema()

    def get_connection(self) -> sqlite3.Connection:
        """Create or return a configured SQLite connection."""
        if self._memory_conn is not None:
            return self._memory_conn

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def initialize_schema(self) -> None:
        """Create database tables if they do not exist."""
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    repository TEXT NOT NULL,
                    run_id INTEGER NOT NULL,
                    state TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    data TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_incidents_repo_run
                ON incidents (repository, run_id);
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_incidents_state
                ON incidents (state);
                """
            )
