"""Shared pytest fixtures for Guardrail-CI tests."""

from __future__ import annotations

import pytest

from guardrail_ci.config.settings import AppSettings, GitHubSettings, ModelSettings


@pytest.fixture
def github_settings() -> GitHubSettings:
    """Fixture providing test GitHub settings with allowlisted repo."""
    return GitHubSettings(
        token="ghp_testdummytoken000000000000000000000",
        allowed_repos=["owner/test-repo"],
        api_base="https://api.github.com",
        max_log_lines=100,
    )


@pytest.fixture
def model_settings() -> ModelSettings:
    """Fixture providing test Model settings."""
    return ModelSettings(
        provider="openai",
        api_base="https://api.openai.com/v1",
        api_key="sk-testkey00000000000000000000",
        name="gpt-4o-mini",
        max_tokens=2048,
        timeout_seconds=10,
    )


@pytest.fixture
def app_settings(github_settings: GitHubSettings, model_settings: ModelSettings, tmp_path: str) -> AppSettings:
    """Fixture providing full AppSettings pointing to temporary file paths."""
    return AppSettings(
        github=github_settings,
        model=model_settings,
        database_path=f"{tmp_path}/test.db",
        audit_log_path=f"{tmp_path}/audit.jsonl",
    )
