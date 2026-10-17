"""Evidence collection orchestration from GitHub Actions runs."""

from __future__ import annotations

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.core.models import EvidenceItem
from guardrail_ci.evidence.redactor import redact_secrets


class EvidenceCollector:
    """Collect and sanitize evidence from a failed GitHub Actions run."""

    def __init__(self, github_client: GitHubClient) -> None:
        self._github = github_client

    def collect(self, repo: str, run_id: int) -> list[EvidenceItem]:
        """Gather sanitized evidence from failed jobs in a workflow run."""
        evidence: list[EvidenceItem] = []

        jobs = self._github.get_workflow_jobs(repo, run_id)
        failed_jobs = [j for j in jobs if j.conclusion == "failure"]

        for job in failed_jobs:
            raw_logs = self._github.get_job_logs(repo, job.id)
            sanitized_logs = redact_secrets(raw_logs)

            failed_steps = [s for s in job.steps if s.conclusion == "failure"]
            if failed_steps:
                for step in failed_steps:
                    evidence.append(
                        EvidenceItem(
                            job=job.name,
                            step=step.name,
                            excerpt=_extract_relevant_excerpt(sanitized_logs, step.name),
                            source=f"job:{job.id}/step:{step.number}",
                            is_observation=True,
                        )
                    )
            else:
                # If step conclusions are not detailed, extract tail
                evidence.append(
                    EvidenceItem(
                        job=job.name,
                        step="(unspecified failed step)",
                        excerpt=_tail_excerpt(sanitized_logs, max_lines=40),
                        source=f"job:{job.id}/logs_tail",
                        is_observation=True,
                    )
                )

        return evidence


def _extract_relevant_excerpt(logs: str, step_name: str, context_lines: int = 35) -> str:
    """Extract log lines relevant to a failed step."""
    if not logs:
        return "[No logs recorded]"

    lines = logs.splitlines()
    step_lower = step_name.lower()

    # Look for step indicator in logs
    for i, line in enumerate(lines):
        if step_lower in line.lower() or "error" in line.lower() or "failed" in line.lower():
            start = max(0, i - 5)
            end = min(len(lines), i + context_lines)
            return "\n".join(lines[start:end])

    return _tail_excerpt(logs, max_lines=context_lines)


def _tail_excerpt(logs: str, max_lines: int = 40) -> str:
    """Return the final lines of the log text."""
    if not logs:
        return "[No logs recorded]"
    lines = logs.splitlines()
    return "\n".join(lines[-max_lines:])
