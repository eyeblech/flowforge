"""FastAPI application providing REST endpoints, webhook ingestion, and web dashboard."""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from flowforge.core.graph import WorkflowGraph
from flowforge.core.models import WorkflowDefinition, WorkflowRun
from flowforge.core.parser import load_workflow_file, parse_workflow_str
from flowforge.engine.runner import WorkflowEngine
from flowforge.server.dashboard import get_dashboard_html
from flowforge.storage.base import BaseStorage
from flowforge.storage.sqlite import SQLiteStorage
from flowforge.triggers.cron import CronScheduler
from flowforge.triggers.file_watcher import FileWatcherTrigger
from flowforge.triggers.webhook import verify_webhook_token
from flowforge.utils.logger import logger


class RunTriggerRequest(BaseModel):
    """Payload for manual workflow triggering via API."""
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


class ValidateWorkflowRequest(BaseModel):
    """Payload for syntax and DAG cycle validation."""
    yaml_content: str


class RunCustomWorkflowRequest(BaseModel):
    """Payload for running a custom or edited workflow directly from the studio."""
    yaml_content: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)


def generate_mermaid_graph(wf: WorkflowDefinition, run: Optional[WorkflowRun] = None) -> str:
    """Generate Mermaid flowchart TD definition for a workflow, optionally styled with run statuses."""
    lines = [
        "graph TD",
        "  %% FlowForge Directed Acyclic Graph",
        "  classDef default fill:#1e293b,stroke:#475569,stroke-width:1.5px,color:#f8fafc;",
        "  classDef statusSuccess fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#ecfdf5;",
        "  classDef statusFailed fill:#4c0519,stroke:#f43f5e,stroke-width:2px,color:#fff1f2;",
        "  classDef statusRunning fill:#0c4a6e,stroke:#38bdf8,stroke-width:2px,color:#f0f9ff;",
        "  classDef statusSkipped fill:#1e293b,stroke:#64748b,stroke-width:1px,stroke-dasharray: 4 4,color:#94a3b8;",
    ]

    action_icons = {
        "shell": "💻",
        "http": "🌐",
        "transform": "⚡",
        "file": "📄",
        "llm": "🤖",
        "notify": "🔔",
        "sql": "🗄️",
        "delay": "⏱️",
    }

    step_keys: Dict[str, str] = {}
    for step in wf.steps:
        safe_key = "node_" + "".join(c if c.isalnum() or c == "_" else "_" for c in step.id)
        step_keys[step.id] = safe_key
        icon = action_icons.get(step.action, "⚙️")
        name = (step.name or step.id).replace('"', "'")
        lines.append(f'  {safe_key}["{icon} {name}<br/><sub style=\'opacity:0.7\'>{step.action} | {step.id}</sub>"]')

    for step in wf.steps:
        target_key = step_keys[step.id]
        for dep in step.depends_on:
            dep_key = step_keys.get(dep, "node_" + dep)
            lines.append(f"  {dep_key} --> {target_key}")

    if run and run.step_runs:
        for step_id, st in run.step_runs.items():
            k = step_keys.get(step_id)
            if not k:
                continue
            status_val = st.status.value if hasattr(st.status, "value") else str(st.status)
            if status_val == "success":
                lines.append(f"  class {k} statusSuccess;")
            elif status_val == "failed":
                lines.append(f"  class {k} statusFailed;")
            elif status_val == "running":
                lines.append(f"  class {k} statusRunning;")
            elif status_val == "skipped":
                lines.append(f"  class {k} statusSkipped;")

    return "\n".join(lines)


def _get_dashboard_html() -> str:
    """Return dashboard HTML (delegates to get_dashboard_html)."""
    return get_dashboard_html()


def create_app(
    storage: Optional[BaseStorage] = None,
    workflows_dir: Optional[str] = None,
) -> FastAPI:
    """Create and configure the FlowForge FastAPI application."""
    db_storage = storage or SQLiteStorage("flowforge.db")
    engine = WorkflowEngine(storage=db_storage)
    cron_scheduler = CronScheduler(engine=engine)
    file_watcher = FileWatcherTrigger(engine=engine)

    effective_dir = workflows_dir or ("examples" if Path("examples").is_dir() else None)

    # Load workflows from directory if provided
    workflow_registry: Dict[str, WorkflowDefinition] = {}
    if effective_dir and Path(effective_dir).is_dir():
        for p in Path(effective_dir).glob("*.yaml"):
            try:
                wf = load_workflow_file(p)
                workflow_registry[wf.id] = wf
                db_storage.save_workflow(wf)
                cron_scheduler.register_workflow(wf)
                file_watcher.register_workflow(wf)
                logger.info("Loaded workflow '%s' from %s", wf.id, p)
            except Exception as e:
                logger.error("Failed loading workflow %s: %s", p, e)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await cron_scheduler.start()
        await file_watcher.start()
        logger.info("FlowForge server background triggers started.")
        yield
        await cron_scheduler.stop()
        await file_watcher.stop()
        db_storage.close()
        logger.info("FlowForge server shut down cleanly.")

    app = FastAPI(
        title="FlowForge API & Dashboard",
        description="Resilient Workflow Automation & Task Orchestration Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Attach shared instances to app state
    app.state.storage = db_storage
    app.state.engine = engine
    app.state.workflows = workflow_registry
    app.state.workflows_dir = effective_dir

    # ------------------- REST API Endpoints -------------------

    @app.get("/api/v1/health")
    async def get_health() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "version": "0.1.0",
            "workflows_loaded": len(app.state.workflows),
        }

    @app.get("/api/v1/templates")
    async def list_templates() -> List[Dict[str, Any]]:
        """Return sample workflow templates loaded from the workflows directory."""
        templates = []
        target_dir = app.state.workflows_dir
        if target_dir and Path(target_dir).is_dir():
            for p in sorted(Path(target_dir).glob("*.yaml")):
                try:
                    content = p.read_text(encoding="utf-8")
                    wf = load_workflow_file(p)
                    templates.append({
                        "id": wf.id,
                        "name": wf.name,
                        "filename": p.name,
                        "description": wf.description or "",
                        "yaml": content,
                        "step_count": len(wf.steps),
                    })
                except Exception:
                    pass
        return templates

    @app.get("/api/v1/workflows")
    async def list_workflows() -> List[Dict[str, Any]]:
        wfs = app.state.storage.list_workflows()
        # Merge in-memory registry
        seen = {wf.id for wf in wfs}
        for wf in app.state.workflows.values():
            if wf.id not in seen:
                wfs.append(wf)
        return [wf.model_dump() for wf in wfs]

    @app.get("/api/v1/workflows/{workflow_id}")
    async def get_workflow(workflow_id: str) -> Dict[str, Any]:
        wf = app.state.workflows.get(workflow_id) or app.state.storage.get_workflow(workflow_id)
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return wf.model_dump()

    @app.get("/api/v1/workflows/{workflow_id}/dag")
    async def get_workflow_dag(
        workflow_id: str,
        run_id: Optional[str] = Query(None),
    ) -> Dict[str, Any]:
        """Return Mermaid DAG definition and graph topology analysis for workflow."""
        wf = app.state.workflows.get(workflow_id) or app.state.storage.get_workflow(workflow_id)
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        run = None
        if run_id:
            run = app.state.storage.get_run(run_id)

        mermaid_code = generate_mermaid_graph(wf, run=run)
        graph = WorkflowGraph(wf)
        return {
            "workflow_id": wf.id,
            "name": wf.name,
            "mermaid": mermaid_code,
            "execution_order": graph.topological_order(),
            "root_steps": graph.get_root_steps(),
            "step_count": len(wf.steps),
        }

    @app.post("/api/v1/workflows/validate")
    async def validate_workflow_endpoint(req: ValidateWorkflowRequest) -> Dict[str, Any]:
        """Validate workflow YAML syntax, Pydantic schema, and DAG cycle freedom."""
        try:
            wf = parse_workflow_str(req.yaml_content)
            graph = WorkflowGraph(wf)
            order = graph.topological_order()
            roots = graph.get_root_steps()
            mermaid_code = generate_mermaid_graph(wf)
            return {
                "valid": True,
                "id": wf.id,
                "name": wf.name,
                "description": wf.description or "",
                "step_count": len(wf.steps),
                "execution_order": order,
                "root_steps": roots,
                "mermaid": mermaid_code,
            }
        except Exception as e:
            return {
                "valid": False,
                "error": str(e),
            }

    @app.post("/api/v1/workflows/run-custom")
    async def run_custom_workflow_endpoint(req: RunCustomWorkflowRequest) -> Dict[str, Any]:
        """Parse, register, and execute custom YAML workflow from the Studio."""
        try:
            wf = parse_workflow_str(req.yaml_content)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid workflow syntax: {e}")

        # Register workflow so runs can be tracked and inspected
        app.state.storage.save_workflow(wf)
        app.state.workflows[wf.id] = wf

        run = await app.state.engine.execute(
            workflow=wf,
            trigger_type="studio_editor",
            trigger_payload=req.payload,
            initial_context=req.context,
        )
        return run.model_dump()

    @app.post("/api/v1/workflows/{workflow_id}/run")
    async def trigger_workflow(
        workflow_id: str, request_data: RunTriggerRequest
    ) -> Dict[str, Any]:
        wf = app.state.workflows.get(workflow_id) or app.state.storage.get_workflow(workflow_id)
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")

        run = await app.state.engine.execute(
            workflow=wf,
            trigger_type="manual_api",
            trigger_payload=request_data.payload,
            initial_context=request_data.context,
        )
        return run.model_dump()

    @app.get("/api/v1/runs")
    async def list_runs(
        workflow_id: Optional[str] = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ) -> List[Dict[str, Any]]:
        runs = app.state.storage.list_runs(workflow_id=workflow_id, limit=limit)
        return [r.model_dump() for r in runs]

    @app.get("/api/v1/runs/{run_id}")
    async def get_run(run_id: str) -> Dict[str, Any]:
        run = app.state.storage.get_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        return run.model_dump()

    # ------------------- Webhook Ingestion -------------------

    @app.post("/api/v1/webhooks/{workflow_id}")
    @app.get("/api/v1/webhooks/{workflow_id}")
    async def receive_webhook(
        workflow_id: str,
        request: Request,
        x_flowforge_token: Optional[str] = Header(None),
        authorization: Optional[str] = Header(None),
    ) -> JSONResponse:
        wf = app.state.workflows.get(workflow_id) or app.state.storage.get_workflow(workflow_id)
        if not wf:
            return JSONResponse(
                status_code=404,
                content={"error": f"Workflow '{workflow_id}' not found"},
            )

        # Find webhook trigger configuration
        webhook_triggers = [t for t in wf.triggers if t.type.value == "webhook"]
        if not webhook_triggers:
            return JSONResponse(
                status_code=400,
                content={"error": f"Workflow '{workflow_id}' does not have a webhook trigger defined."},
            )

        cfg = webhook_triggers[0].config
        expected_token = cfg.get("secret_token")

        # Determine provided token
        provided_token = x_flowforge_token
        if not provided_token and authorization:
            if authorization.startswith("Bearer "):
                provided_token = authorization.split("Bearer ", 1)[1].strip()
            else:
                provided_token = authorization.strip()

        if not verify_webhook_token(expected_token, provided_token):
            return JSONResponse(
                status_code=401,
                content={"error": "Unauthorized: Invalid webhook secret token."},
            )

        # Parse request payload
        try:
            body = await request.json()
        except Exception:
            body = (await request.body()).decode("utf-8", errors="replace")

        payload = {
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "body": body,
        }

        # Launch workflow asynchronously
        run = await app.state.engine.execute(
            workflow=wf,
            trigger_type="webhook",
            trigger_payload=payload,
        )

        return JSONResponse(
            status_code=202,
            content={
                "message": "Webhook accepted and workflow triggered",
                "run_id": run.run_id,
                "status": run.status.value,
            },
        )

    # ------------------- Embedded Web Dashboard -------------------

    @app.get("/", response_class=HTMLResponse)
    async def dashboard() -> str:
        return get_dashboard_html()

    return app
