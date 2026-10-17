"""Guardrail-CI command-line interface."""

from __future__ import annotations

import sys

import click
from rich.console import Console

from guardrail_ci.adapters.github.client import GitHubClient
from guardrail_ci.adapters.model.openai_compat import OpenAICompatAdapter
from guardrail_ci.audit.logger import AuditLogger
from guardrail_ci.cli.formatters import render_rich_report
from guardrail_ci.config.settings import AppSettings
from guardrail_ci.core.models import IncidentState
from guardrail_ci.core.orchestrator import Orchestrator
from guardrail_ci.policy.engine import PolicyEngine

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


@click.group()
@click.version_option(version="0.1.0", prog_name="guardrail-ci")
def cli() -> None:
    """Guardrail-CI: Security-conscious AI assistant for GitHub Actions CI failure investigation."""


@cli.command()
@click.option(
    "--repo",
    required=True,
    help="Target repository identifier in owner/repository format (e.g., octocat/Hello-World)",
)
@click.option(
    "--run-id",
    required=True,
    type=int,
    help="GitHub Actions workflow run identifier to investigate",
)
@click.option(
    "--output",
    type=click.Choice(["rich", "json"], case_sensitive=False),
    default="rich",
    help="Output formatting presentation style",
)
def investigate(repo: str, run_id: int, output: str) -> None:
    """Investigate a failed GitHub Actions workflow run without repository writes."""
    settings = AppSettings()

    github_client = GitHubClient(settings.github)
    model_adapter = OpenAICompatAdapter(settings.model)
    policy_engine = PolicyEngine()
    audit_logger = AuditLogger(settings.audit_log_path)

    orchestrator = Orchestrator(
        github_client=github_client,
        model_adapter=model_adapter,
        policy_engine=policy_engine,
        audit_logger=audit_logger,
    )

    try:
        with console.status(f"[bold green]Investigating workflow run {run_id} on {repo}..."):
            incident = orchestrator.investigate(repo, run_id)
    finally:
        github_client.close()

    if output == "json":
        click.echo(incident.model_dump_json(indent=2))
    else:
        render_rich_report(incident, console)

    sys.exit(0 if incident.state != IncidentState.FAILED else 1)


if __name__ == "__main__":
    cli()
