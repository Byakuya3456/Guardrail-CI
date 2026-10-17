"""GitHub REST API client for Actions workflow data retrieval."""

from __future__ import annotations

from typing import Any, cast

import httpx

from guardrail_ci.adapters.github.models import WorkflowJob, WorkflowRun
from guardrail_ci.config.settings import GitHubSettings
from guardrail_ci.core.exceptions import (
    GitHubAuthError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    RepositoryNotAllowedError,
)


class GitHubClient:
    """Read-only client for GitHub Actions workflow runs, jobs, and logs."""

    def __init__(self, settings: GitHubSettings, http_client: httpx.Client | None = None) -> None:
        self._settings = settings
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.token:
            headers["Authorization"] = f"Bearer {settings.token}"

        self._client = http_client or httpx.Client(
            base_url=settings.api_base,
            headers=headers,
            timeout=30.0,
        )

    def _check_repo_allowed(self, repo: str) -> None:
        """Verify repository identifier is allowed by configuration."""
        if self._settings.allowed_repos and repo not in self._settings.allowed_repos:
            raise RepositoryNotAllowedError(
                f"Repository '{repo}' is not in the allowed list: {self._settings.allowed_repos}"
            )

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Process API HTTP response codes uniformly."""
        if response.status_code == 401:
            raise GitHubAuthError("GitHub authentication failed. Check your GITHUB_TOKEN.")
        if response.status_code == 403:
            if "rate limit" in response.text.lower():
                raise GitHubRateLimitError("GitHub API rate limit exceeded.")
            raise GitHubAuthError("Insufficient GitHub permissions for this operation.")
        if response.status_code == 404:
            raise GitHubNotFoundError(f"Requested GitHub resource not found: {response.url}")
        response.raise_for_status()
        return cast(dict[str, Any], response.json())

    def get_workflow_run(self, repo: str, run_id: int) -> WorkflowRun:
        """Fetch metadata for a specific workflow run."""
        self._check_repo_allowed(repo)
        resp = self._client.get(f"/repos/{repo}/actions/runs/{run_id}")
        data = self._handle_response(resp)
        return WorkflowRun.model_validate(data)

    def get_workflow_jobs(self, repo: str, run_id: int) -> list[WorkflowJob]:
        """Fetch all jobs for a specific workflow run."""
        self._check_repo_allowed(repo)
        resp = self._client.get(f"/repos/{repo}/actions/runs/{run_id}/jobs")
        data = self._handle_response(resp)
        return [WorkflowJob.model_validate(job) for job in data.get("jobs", [])]

    def get_job_logs(self, repo: str, job_id: int) -> str:
        """Retrieve bounded log content for a failed job."""
        self._check_repo_allowed(repo)
        resp = self._client.get(
            f"/repos/{repo}/actions/jobs/{job_id}/logs",
            follow_redirects=True,
        )
        if resp.status_code == 404:
            return "[Logs not available]"
        if resp.status_code == 401:
            raise GitHubAuthError("GitHub authentication failed when fetching logs.")
        if resp.status_code == 403:
            raise GitHubAuthError("Forbidden from fetching logs.")
        resp.raise_for_status()

        lines = resp.text.splitlines()
        max_lines = self._settings.max_log_lines
        if len(lines) > max_lines:
            lines = lines[-max_lines:]
        return "\n".join(lines)

    def create_branch(self, repo: str, branch_name: str, sha: str) -> dict[str, Any]:
        """Create a new git reference branch. Never merges."""
        self._check_repo_allowed(repo)
        resp = self._client.post(
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch_name}", "sha": sha},
        )
        return self._handle_response(resp)

    def create_or_update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict[str, Any]:
        """Commit a modified file to a branch on GitHub."""
        import base64
        self._check_repo_allowed(repo)
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
        payload: dict[str, Any] = {
            "message": message,
            "content": encoded_content,
            "branch": branch,
        }
        if sha:
            payload["sha"] = sha
        resp = self._client.put(f"/repos/{repo}/contents/{path}", json=payload)
        return self._handle_response(resp)

    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> dict[str, Any]:
        """Open a pull request for human review. Never merges or deploys."""
        self._check_repo_allowed(repo)
        resp = self._client.post(
            f"/repos/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": False,
            },
        )
        return self._handle_response(resp)

    def close(self) -> None:
        """Close internal HTTP client resources."""
        self._client.close()
