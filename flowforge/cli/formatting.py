"""Rich formatting helpers and terminal visualizations for FlowForge CLI."""

from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from flowforge.core.models import StepRun, StepStatus, WorkflowDefinition, WorkflowRun, WorkflowStatus
from flowforge.utils.logger import get_console


def get_status_text(status: Any) -> Text:
    """Format status with colored icon and text."""
    val = status.value if hasattr(status, "value") else str(status)
    if val in ("success", "completed"):
        return Text("● SUCCESS", style="bold green")
    elif val == "failed":
        return Text("✖ FAILED", style="bold red")
    elif val == "running":
        return Text("↻ RUNNING", style="bold cyan")
    elif val == "skipped":
        return Text("○ SKIPPED", style="bold yellow")
    elif val == "partially_failed":
        return Text("⚠ PARTIAL", style="bold yellow")
    return Text(f"● {val.upper()}", style="dim")


def render_banner(console: Console) -> None:
    """Render startup ASCII banner."""
    banner = """[bold cyan]╔═╗┬  ┌─┐┬ ┬[/bold cyan][bold blue]╔═╗┌─┐┬─┐┌─┐┌─┐[/bold blue]
[bold cyan]╠╣ │  │ ││││[/bold cyan][bold blue]╠╣ │ │├┬┘│ ┬├┤ [/bold blue]
[bold cyan]╚  ┴─┘└─┘└┴┘[/bold cyan][bold blue]╚  └─┘┴└─└─┘└─┘[/bold blue]
[dim italic]Developer-first async workflow automation engine[/dim italic]"""
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


def render_run_summary(console: Console, run: WorkflowRun, workflow: WorkflowDefinition) -> None:
    """Render a comprehensive visual summary table of a workflow execution."""
    console.print()
    table = Table(
        title=f"Execution Summary: [bold cyan]{workflow.name}[/bold cyan] ([dim]{run.run_id}[/dim])",
        title_justify="left",
        border_style="dim",
        header_style="bold cyan",
    )

    table.add_column("Step ID", style="bold")
    table.add_column("Action", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Attempt", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Error / Notes", style="dim")

    step_def_map = {s.id: s for s in workflow.steps}

    for step_id, step_run in run.step_runs.items():
        step_def = step_def_map.get(step_id)
        action_name = step_def.action if step_def else "unknown"
        duration_str = f"{step_run.duration_ms:.1f}ms" if step_run.duration_ms else "-"
        note = step_run.error or ""
        if not note and step_run.status == StepStatus.SKIPPED and step_run.logs:
            note = step_run.logs[0]

        table.add_row(
            step_id,
            action_name,
            get_status_text(step_run.status),
            str(step_run.attempt),
            duration_str,
            note[:50] + "..." if len(note) > 50 else note,
        )

    console.print(table)
    console.print()

    # Overall Outcome Card
    total_time = f"{run.duration_ms:.2f}ms" if run.duration_ms else "0ms"
    summary_text = (
        f"Status: {get_status_text(run.status)}  │  "
        f"Total Duration: [bold]{total_time}[/bold]  │  "
        f"Trigger: [cyan]{run.trigger_type}[/cyan]"
    )
    if run.error:
        summary_text += f"\n[red]Failure: {run.error}[/red]"

    border_color = "green" if run.status == WorkflowStatus.SUCCESS else "red"
    console.print(Panel(summary_text, border_style=border_color, title="Run Result", title_align="left"))


def render_runs_table(console: Console, runs: List[WorkflowRun]) -> None:
    """Render list of workflow execution runs in a table."""
    table = Table(
        title="Recent Workflow Runs",
        border_style="dim",
        header_style="bold cyan",
    )

    table.add_column("Run ID", style="bold cyan")
    table.add_column("Workflow ID", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Trigger", style="dim")
    table.add_column("Started At", style="dim")
    table.add_column("Duration", justify="right")

    for r in runs:
        dur = f"{r.duration_ms:.1f}ms" if r.duration_ms else "-"
        started = r.started_at.strftime("%Y-%m-%d %H:%M:%S") if r.started_at else "-"
        table.add_row(
            r.run_id,
            r.workflow_id,
            get_status_text(r.status),
            r.trigger_type,
            started,
            dur,
        )

    console.print(table)


def render_dag_tree(console: Console, workflow: WorkflowDefinition) -> None:
    """Render a visual tree of workflow steps and their dependencies."""
    tree = Tree(f"[bold cyan]{workflow.name}[/bold cyan] ([dim]{workflow.id}[/dim])")
    for step in workflow.steps:
        deps = f" [dim](depends on: {', '.join(step.depends_on)})[/dim]" if step.depends_on else ""
        tree.add(f"[bold]{step.id}[/bold] → [yellow]{step.action}[/yellow]{deps}")
    console.print(tree)
