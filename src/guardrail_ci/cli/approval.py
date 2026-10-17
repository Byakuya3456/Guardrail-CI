"""Interactive approval prompts for remote repository write operations."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from guardrail_ci.core.models import Incident


def request_approval(incident: Incident, console: Console | None = None) -> bool:
    """Present proposed changes and risk evaluation, requiring explicit human approval.

    Returns True only if the user explicitly confirms (default: No).
    """
    c = console or Console()

    c.print(
        Panel(
            "[bold yellow]⚠️  HUMAN APPROVAL GATE REQUIRED[/bold yellow]\n\n"
            "Guardrail-CI is preparing to publish a remediation branch and open a Pull Request.\n"
            "[bold cyan]Security Guarantee:[/bold cyan] This will [bold]NEVER[/bold] automatically merge or deploy code.\n"
            "All modifications will be submitted as an open PR for human review.",
            title="[bold yellow]Remote Repository Write Request[/bold yellow]",
            expand=False,
        )
    )

    if incident.remediation_plan and incident.remediation_plan.files:
        c.print("\n[bold]Proposed File Changes:[/bold]")
        for patch_file in incident.remediation_plan.files:
            c.print(f"\n[green]• {patch_file.path}[/green]")
            if patch_file.diff:
                c.print(Syntax(patch_file.diff, "diff", theme="monokai", line_numbers=True))

    if incident.remediation_plan and incident.remediation_plan.risks:
        c.print("\n[bold red]Known Risks & Side-Effects:[/bold red]")
        for risk in incident.remediation_plan.risks:
            c.print(f"  ⚠ {risk}")

    c.print()
    return click.confirm(
        "Do you approve creating a remote branch and pull request with these changes?",
        default=False,
    )
