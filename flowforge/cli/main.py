"""FlowForge CLI entry point and command implementations."""

import asyncio
from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from flowforge.actions.base import registry as action_registry
from flowforge.cli.formatting import (
    get_console,
    get_status_text,
    render_banner,
    render_dag_tree,
    render_run_summary,
    render_runs_table,
)
from flowforge.core.graph import WorkflowGraph, WorkflowGraphError
from flowforge.core.models import WorkflowStatus
from flowforge.core.parser import WorkflowParseError, load_workflow_file
from flowforge.engine.events import EngineEvent, EventType
from flowforge.engine.runner import WorkflowEngine
from flowforge.storage.sqlite import SQLiteStorage

app = typer.Typer(
    name="flowforge",
    help="⚡ FlowForge: A developer-first workflow automation and task orchestration engine.",
    add_completion=False,
    no_args_is_help=True,
)
runs_app = typer.Typer(name="runs", help="Manage and inspect workflow execution runs.")
app.add_typer(runs_app, name="runs")

console = get_console()


@app.command("run")
def run_command(
    workflow_path: str = typer.Argument(..., help="Path to workflow YAML or JSON file."),
    db_path: str = typer.Option("flowforge.db", "--db", help="Path to SQLite persistence database."),
    params: list[str] | None = typer.Option(
        None, "--param", "-p", help="Key=Value parameters passed to workflow trigger payload."
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose debug logging."),
) -> None:
    """Execute a workflow file locally with real-time telemetry."""
    render_banner(console)

    path = Path(workflow_path)
    if not path.is_file():
        console.print(f"[bold red]Error:[/bold red] Workflow file not found: [yellow]{workflow_path}[/yellow]")
        raise typer.Exit(code=1)

    try:
        workflow = load_workflow_file(path)
    except Exception as e:
        console.print(f"[bold red]Failed to load workflow:[/bold red] {e}")
        raise typer.Exit(code=1)

    console.print(f"Loaded workflow: [bold cyan]{workflow.name}[/bold cyan] ({len(workflow.steps)} steps)")

    # Parse trigger params
    trigger_payload = {}
    if params:
        for p in params:
            if "=" in p:
                k, v = p.split("=", 1)
                trigger_payload[k.strip()] = v.strip()

    storage = SQLiteStorage(db_path)
    storage.save_workflow(workflow)
    engine = WorkflowEngine(storage=storage)

    # Attach live event logger
    def on_event(event: EngineEvent):
        if event.event_type == EventType.STEP_STARTED:
            console.print(f"  [cyan]▶ Running step:[/cyan] [bold]{event.step_id}[/bold]")
        elif event.event_type == EventType.STEP_COMPLETED:
            console.print(f"  [green]✔ Completed step:[/green] [bold]{event.step_id}[/bold]")
        elif event.event_type == EventType.STEP_FAILED:
            console.print(f"  [red]✖ Failed step:[/red] [bold]{event.step_id}[/bold] [dim]({event.error})[/dim]")
        elif event.event_type == EventType.STEP_SKIPPED:
            console.print(f"  [yellow]○ Skipped step:[/yellow] [bold]{event.step_id}[/bold]")
        elif event.event_type == EventType.STEP_RETRYING:
            console.print(f"  [yellow]↻ Retrying step:[/yellow] [bold]{event.step_id}[/bold] [dim]({event.error})[/dim]")

    engine.event_bus.subscribe(on_event)

    console.print("[dim]Starting execution pipeline...[/dim]")
    run_result = asyncio.run(
        engine.execute(
            workflow=workflow,
            trigger_type="cli",
            trigger_payload=trigger_payload,
        )
    )

    render_run_summary(console, run_result, workflow)
    storage.close()

    if run_result.status != WorkflowStatus.SUCCESS:
        raise typer.Exit(code=1)


@app.command("validate")
def validate_command(
    workflow_path: str = typer.Argument(..., help="Path to workflow YAML file.")
) -> None:
    """Validate workflow syntax, schema, and DAG structure (cycle detection)."""
    render_banner(console)
    path = Path(workflow_path)
    if not path.is_file():
        console.print(f"[bold red]Error:[/bold red] File not found: {workflow_path}")
        raise typer.Exit(code=1)

    try:
        wf = load_workflow_file(path)
        graph = WorkflowGraph(wf)
        order = graph.topological_order()

        console.print(f"[bold green]✔ Workflow '{wf.name}' ({wf.id}) is valid![/bold green]")
        console.print(f"Steps: [bold]{len(wf.steps)}[/bold]")
        console.print(f"Execution order: [dim]{' → '.join(order)}[/dim]")
    except (WorkflowParseError, WorkflowGraphError) as e:
        console.print(f"[bold red]Validation Error:[/bold red] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]Unexpected Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("tree")
def tree_command(
    workflow_path: str = typer.Argument(..., help="Path to workflow YAML file.")
) -> None:
    """Render the DAG tree and step dependencies in the terminal."""
    try:
        wf = load_workflow_file(workflow_path)
        render_dag_tree(console, wf)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1)


@app.command("actions")
def actions_command() -> None:
    """List all registered action types supported by FlowForge."""
    render_banner(console)
    actions = action_registry.list_actions()
    table = Table(title="Registered FlowForge Actions", border_style="dim", header_style="bold cyan")
    table.add_column("Action Identifier", style="bold cyan")
    table.add_column("Class", style="dim")

    for act in actions:
        cls = action_registry.get(act)
        table.add_row(act, f"{cls.__module__}.{cls.__name__}" if cls else "-")

    console.print(table)


@app.command("serve")
def serve_command(
    workflows_dir: str = typer.Option("./examples", "--workflows-dir", "-w", help="Directory containing workflow YAMLs."),
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address."),
    port: int = typer.Option(8000, "--port", "-p", help="Bind port."),
    db_path: str = typer.Option("flowforge.db", "--db", help="Path to SQLite persistence database."),
    demo: bool = typer.Option(False, "--demo", help="Enable public demo sandbox mode (restricts custom shell execution)."),
) -> None:
    """Launch the FlowForge Web Dashboard, REST API, and Trigger Server."""
    import os

    import uvicorn

    from flowforge.server.app import create_app

    env_host = os.environ.get("HOST")
    if env_host and host == "127.0.0.1":
        host = env_host

    env_port = os.environ.get("PORT")
    if env_port and port == 8000:
        try:
            port = int(env_port)
        except ValueError:
            pass

    demo_mode = demo or (os.environ.get("FLOWFORGE_DEMO", "").lower() in ("1", "true", "yes"))
    if demo_mode:
        os.environ["FLOWFORGE_DEMO"] = "true"

    render_banner(console)
    console.print(f"[bold green]Starting FlowForge Studio & Webhook Server on http://{host}:{port}[/bold green]")
    if demo_mode:
        console.print("[bold yellow]🛡️  Public Demo Mode Active: Custom shell execution restricted.[/bold yellow]")
    console.print(f"Workflows directory: [cyan]{workflows_dir}[/cyan]")
    console.print(f"Database: [cyan]{db_path}[/cyan]\n")

    storage = SQLiteStorage(db_path)
    app_instance = create_app(storage=storage, workflows_dir=workflows_dir, demo_mode=demo_mode)
    uvicorn.run(app_instance, host=host, port=port, log_level="info")


@app.command("init")
def init_command(
    directory: str = typer.Argument(".", help="Target directory for new project.")
) -> None:
    """Scaffold a new FlowForge automation project with sample workflows and config."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    workflows_folder = target / "workflows"
    workflows_folder.mkdir(exist_ok=True)

    sample_yaml = """# FlowForge Sample Workflow
id: sample_greeting_pipeline
name: Sample Greeting Pipeline
description: Demonstrates variables, shell tasks, data transforms, and file output
version: "1.0"

steps:
  - id: check_system
    name: Check System Info
    action: shell
    with:
      command: "uname -a || ver"

  - id: build_message
    name: Build Formatted Message
    action: transform
    depends_on: [check_system]
    with:
      value:
        greeting: "Hello from FlowForge!"
        system: "{{ steps.check_system.output.stdout }}"
        timestamp: "{{ now().isoformat() }}"

  - id: save_output
    name: Save Result to Disk
    action: file
    depends_on: [build_message]
    with:
      operation: write
      path: "./output/greeting.json"
      content: "{{ steps.build_message.output | to_json }}"
"""
    sample_file = workflows_folder / "sample_pipeline.yaml"
    if not sample_file.exists():
        sample_file.write_text(sample_yaml, encoding="utf-8")

    console.print(f"[bold green]✔ Initialized FlowForge project in [cyan]{target.resolve()}[/cyan][/bold green]")
    console.print("Sample workflow created: [bold]workflows/sample_pipeline.yaml[/bold]")
    console.print("\nRun it now with:")
    console.print("  [cyan]flowforge run workflows/sample_pipeline.yaml[/cyan]")


# Subcommands for `flowforge runs`
@runs_app.command("list")
def runs_list_command(
    db_path: str = typer.Option("flowforge.db", "--db", help="Path to SQLite persistence database."),
    workflow: str | None = typer.Option(None, "--workflow", "-w", help="Filter by workflow ID."),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of records to display."),
) -> None:
    """List execution runs stored in the database."""
    storage = SQLiteStorage(db_path)
    runs = storage.list_runs(workflow_id=workflow, limit=limit)
    if not runs:
        console.print("[dim]No execution runs found.[/dim]")
    else:
        render_runs_table(console, runs)
    storage.close()


@runs_app.command("get")
def runs_get_command(
    run_id: str = typer.Argument(..., help="Run ID to inspect."),
    db_path: str = typer.Option("flowforge.db", "--db", help="Path to SQLite persistence database."),
) -> None:
    """Inspect detailed step execution, output, and logs of a run."""
    storage = SQLiteStorage(db_path)
    run = storage.get_run(run_id)
    if not run:
        console.print(f"[bold red]Error:[/bold red] Run '{run_id}' not found.")
        raise typer.Exit(code=1)

    console.print(Panel(
        f"Workflow ID: [bold]{run.workflow_id}[/bold]\n"
        f"Status: {get_status_text(run.status)}\n"
        f"Trigger: [cyan]{run.trigger_type}[/cyan]\n"
        f"Duration: [bold]{run.duration_ms or 0:.1f}ms[/bold]\n"
        f"Started: [dim]{run.started_at}[/dim]",
        title=f"Run Details: [bold cyan]{run.run_id}[/bold cyan]",
        title_align="left",
    ))

    table = Table(title="Steps", border_style="dim", header_style="bold cyan")
    table.add_column("Step ID", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Attempt", justify="center")
    table.add_column("Duration", justify="right")
    table.add_column("Error", style="dim")

    for sid, st in run.step_runs.items():
        table.add_row(
            sid,
            get_status_text(st.status),
            str(st.attempt),
            f"{st.duration_ms:.1f}ms" if st.duration_ms else "-",
            st.error or "-",
        )

    console.print(table)
    storage.close()


if __name__ == "__main__":
    app()
