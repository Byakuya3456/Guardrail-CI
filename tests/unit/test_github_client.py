"""Unit tests for GitHub API client."""

from __future__ import annotations

import httpx
import pytest

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.config.settings import GitHubSettings
from guardrail_ci.core.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    RepositoryNotAllowedError,
)


def test_repo_allowlist_enforced(github_settings: GitHubSettings) -> None:
    client = GitHubClient(github_settings)
    with pytest.raises(RepositoryNotAllowedError):
        client.get_workflow_run("disallowed/other-repo", 123)


def test_get_workflow_run_success(github_settings: GitHubSettings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": 999,
                "name": "CI Tests",
                "head_branch": "main",
                "event": "push",
                "status": "completed",
                "conclusion": "failure",
            },
        )

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    client = GitHubClient(github_settings, http_client=mock_http)

    run = client.get_workflow_run("owner/test-repo", 999)
    assert run.id == 999
    assert run.conclusion == "failure"


def test_get_workflow_run_401_auth_error(github_settings: GitHubSettings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"message": "Bad credentials"})

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    client = GitHubClient(github_settings, http_client=mock_http)

    with pytest.raises(GitHubAuthError):
        client.get_workflow_run("owner/test-repo", 999)


def test_get_workflow_run_404_not_found(github_settings: GitHubSettings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"message": "Not Found"})

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    client = GitHubClient(github_settings, http_client=mock_http)

    with pytest.raises(GitHubNotFoundError):
        client.get_workflow_run("owner/test-repo", 999)


def test_get_workflow_run_403_rate_limit(github_settings: GitHubSettings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"message": "API rate limit exceeded"})

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    client = GitHubClient(github_settings, http_client=mock_http)

    with pytest.raises(GitHubRateLimitError):
        client.get_workflow_run("owner/test-repo", 999)


def test_get_job_logs_bounded(github_settings: GitHubSettings) -> None:
    # 150 lines, settings limit is 100
    long_log = "\n".join([f"Log line {i}" for i in range(150)])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=long_log)

    mock_transport = httpx.MockTransport(handler)
    mock_http = httpx.Client(transport=mock_transport, base_url="https://api.github.com")
    client = GitHubClient(github_settings, http_client=mock_http)

    logs = client.get_job_logs("owner/test-repo", 555)
    lines = logs.splitlines()
    assert len(lines) == 100
    assert lines[-1] == "Log line 149"
