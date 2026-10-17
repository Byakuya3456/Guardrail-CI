"""Output formatters for CLI presentation using rich."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from guardrail_ci.core.models import Incident


def render_rich_report(incident: Incident, console: Console) -> None:
    """Render a comprehensive, readable CLI report for an incident."""
    status_color = "green" if "validated" in incident.state.value or incident.state.value == "completed_without_write" else "red"

    # Header Panel
    console.print(
        Panel(
            f"[bold cyan]Incident ID:[/bold cyan] {incident.incident_id}\n"
            f"[bold cyan]Repository:[/bold cyan]  {incident.repository}\n"
            f"[bold cyan]Run ID:[/bold cyan]      {incident.run_id}\n"
            f"[bold cyan]Final State:[/bold cyan] [{status_color}]{incident.state.value}[/{status_color}]",
            title="[bold blue]🛡️ Guardrail-CI Incident Report[/bold blue]",
            expand=False,
        )
    )

    # Diagnosis Details
    if incident.diagnosis:
        d = incident.diagnosis
        conf_pct = f"{int(d.confidence * 100)}%"
        conf_color = "green" if d.confidence >= 0.7 else ("yellow" if d.confidence >= 0.4 else "red")

        console.print(
            Panel(
                f"[bold]Category:[/bold]          [magenta]{d.failure_category.value}[/magenta]\n"
                f"[bold]Confidence:[/bold]        [{conf_color}]{conf_pct}[/{conf_color}]\n"
                f"[bold]Summary:[/bold]           {d.summary}\n"
                f"[bold]Likely Root Cause:[/bold] {d.likely_root_cause}",
                title="[bold green]🔍 Diagnosis & Root Cause[/bold green]",
                expand=False,
            )
        )

        # Evidence Table
        if d.evidence:
            table = Table(title="Observed Evidence", show_header=True, header_style="bold cyan")
            table.add_column("Job", style="dim", width=20)
            table.add_column("Step", width=22)
            table.add_column("Log Excerpt (Redacted & Bounded)")

            for item in d.evidence:
                excerpt_clean = item.excerpt.strip().replace("\r", "")
                if len(excerpt_clean) > 200:
                    excerpt_clean = excerpt_clean[:200] + "..."
                table.add_row(item.job, item.step, excerpt_clean)

            console.print(table)

        # Recommended Next Steps
        if d.recommended_actions:
            console.print("\n[bold yellow]Recommended Next Actions:[/bold yellow]")
            for i, action in enumerate(d.recommended_actions, 1):
                console.print(f"  {i}. {action}")

        # Unresolved Questions (if any)
        if d.unresolved_questions:
            console.print("\n[bold red]Unresolved Questions & Uncertainty:[/bold red]")
            for q in d.unresolved_questions:
                console.print(f"  • {q}")

    # Proposed Patch & Diff Section
    if incident.remediation_plan and incident.remediation_plan.files:
        console.print(
            Panel(
                f"[bold]Description:[/bold]     {incident.remediation_plan.description}\n"
                f"[bold]Intended Effect:[/bold] {incident.remediation_plan.intended_effect}",
                title="[bold cyan]🔧 Proposed Remediation Plan[/bold cyan]",
                expand=False,
            )
        )
        for patch_file in incident.remediation_plan.files:
            console.print(f"\n[bold green]File modified:[/bold green] {patch_file.path}")
            if patch_file.diff:
                console.print(Syntax(patch_file.diff, "diff", theme="monokai", line_numbers=True))

    # Validation Results
    if incident.validation_results:
        val_table = Table(title="Isolated Validation Results", show_header=True, header_style="bold")
        val_table.add_column("Command", width=30)
        val_table.add_column("Status", width=10)
        val_table.add_column("Exit Code", width=10)
        val_table.add_column("Duration", width=10)

        for val in incident.validation_results:
            status_str = "[green]PASSED[/green]" if val.passed else "[red]FAILED[/red]"
            val_table.add_row(
                val.command,
                status_str,
                str(val.exit_code),
                f"{val.duration_seconds}s",
            )
        console.print(val_table)

    # Policy Decisions Summary
    if incident.policy_decisions:
        policy_table = Table(title="Deterministic Policy Decisions", show_header=True, header_style="bold")
        policy_table.add_column("Action", width=25)
        policy_table.add_column("Type", width=15)
        policy_table.add_column("Decision", width=10)
        policy_table.add_column("Reason")

        for dec in incident.policy_decisions:
            dec_str = "[green]ALLOW[/green]" if dec.allowed else "[red]DENY[/red]"
            policy_table.add_row(dec.action, dec.action_type, dec_str, dec.reason)

        console.print(policy_table)

    # Error message if failed
    if incident.error_message:
        console.print(
            Panel(
                f"[bold red]{incident.error_message}[/bold red]",
                title="[bold red]⚠️ Failure Details[/bold red]",
                expand=False,
            )
        )
