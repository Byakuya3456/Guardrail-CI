"""Allowlisted validation commands registry."""

from __future__ import annotations

# Exact allowlisted commands that may be executed during isolated validation
ALLOWLISTED_COMMANDS: set[str] = {
    "pytest",
    "pytest -v",
    "pytest -q",
    "pytest tests/",
    "pytest tests/ -v",
    "ruff check .",
    "ruff check src/ tests/",
    "ruff format --check .",
    "mypy .",
    "mypy src/",
    "python -m unittest",
    "pip check",
    "npm test",
    "npm run lint",
    "npm run build",
}


def is_command_allowlisted(command: str) -> bool:
    """Verify if a command is present in the allowlisted verification registry."""
    normalized = " ".join(command.strip().split())
    return normalized in ALLOWLISTED_COMMANDS
