"""FastAPI application providing REST endpoints, webhook ingestion, and web dashboard."""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Header, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from flowforge.core.models import WorkflowDefinition, WorkflowRun
from flowforge.core.parser import load_workflow_file
from flowforge.engine.runner import WorkflowEngine
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


def create_app(
    storage: Optional[BaseStorage] = None,
    workflows_dir: Optional[str] = None,
) -> FastAPI:
    """Create and configure the FlowForge FastAPI application."""
    db_storage = storage or SQLiteStorage("flowforge.db")
    engine = WorkflowEngine(storage=db_storage)
    cron_scheduler = CronScheduler(engine=engine)
    file_watcher = FileWatcherTrigger(engine=engine)

    # Load workflows from directory if provided
    workflow_registry: Dict[str, WorkflowDefinition] = {}
    if workflows_dir and Path(workflows_dir).is_dir():
        for p in Path(workflows_dir).glob("*.yaml"):
            try:
                wf = load_workflow_file(p)
                workflow_registry[wf.id] = wf
                db_storage.save_workflow(wf)
                cron_scheduler.register_workflow(wf)
                file_watcher.register_workflow(wf)
                logger.info("Loaded workflow '%s' from %s", wf.id, p)
            except Exception as e:
                logger.error("Failed loading workflow %s: %e", p, e)

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

    # ------------------- REST API Endpoints -------------------

    @app.get("/api/v1/health")
    async def get_health() -> Dict[str, Any]:
        return {
            "status": "healthy",
            "version": "0.1.0",
            "workflows_loaded": len(app.state.workflows),
        }

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
        return _get_dashboard_html()

    return app


def _get_dashboard_html() -> str:
    """Return modern, self-contained HTML/CSS/JS dashboard."""
    return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FlowForge Orchestration Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#f0f9ff', 500: '#0284c7', 600: '#0369a1', 900: '#0c4a6e' },
            darkbg: '#0f172a',
            surface: '#1e293b',
            border: '#334155',
          }
        }
      }
    }
  </script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0f19; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
    pre { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
  </style>
</head>
<body class="text-slate-200 min-h-screen flex flex-col">

  <!-- Header Navbar -->
  <header class="bg-slate-900 border-b border-slate-800 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-md">
    <div class="flex items-center space-x-3">
      <div class="bg-gradient-to-tr from-sky-500 to-indigo-600 w-9 h-9 rounded-lg flex items-center justify-center shadow-lg shadow-sky-500/20">
        <i class="fa-solid fa-bolt text-white text-lg"></i>
      </div>
      <div>
        <h1 class="text-lg font-bold text-white tracking-wide">FlowForge</h1>
        <p class="text-xs text-slate-400">Workflow Automation & Orchestration Engine</p>
      </div>
    </div>
    <div class="flex items-center space-x-4">
      <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800">
        <span class="w-2 h-2 mr-1.5 bg-emerald-500 rounded-full animate-pulse"></span> Engine Active
      </span>
      <button onclick="refreshData()" class="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-md border border-slate-700 transition flex items-center space-x-1.5">
        <i class="fa-solid fa-rotate-right"></i> <span>Refresh</span>
      </button>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">

    <!-- Metrics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Total Workflows</span>
          <i class="fa-solid fa-diagram-project text-sky-400 text-base"></i>
        </div>
        <div class="text-2xl font-bold text-white mt-2" id="metric-workflows">0</div>
        <div class="text-xs text-slate-400 mt-1">Loaded in engine</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Execution Runs</span>
          <i class="fa-solid fa-play text-indigo-400 text-base"></i>
        </div>
        <div class="text-2xl font-bold text-white mt-2" id="metric-runs">0</div>
        <div class="text-xs text-slate-400 mt-1">Lifetime executions</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Success Rate</span>
          <i class="fa-solid fa-circle-check text-emerald-400 text-base"></i>
        </div>
        <div class="text-2xl font-bold text-emerald-400 mt-2" id="metric-success">100%</div>
        <div class="text-xs text-slate-400 mt-1">Successful completions</div>
      </div>
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm">
        <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
          <span>Avg Duration</span>
          <i class="fa-solid fa-stopwatch text-amber-400 text-base"></i>
        </div>
        <div class="text-2xl font-bold text-amber-300 mt-2" id="metric-duration">0 ms</div>
        <div class="text-xs text-slate-400 mt-1">Per workflow run</div>
      </div>
    </div>

    <!-- Two Column Layout: Workflows and Recent Executions -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- Left: Registered Workflows -->
      <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <i class="fa-solid fa-network-wired text-sky-400"></i>
            <span>Registered Workflows</span>
          </h2>
          <span class="text-xs text-slate-400" id="workflow-badge">0</span>
        </div>
        <div id="workflows-list" class="space-y-3 overflow-y-auto max-h-[500px] pr-1">
          <p class="text-xs text-slate-400 italic text-center py-6">Loading workflows...</p>
        </div>
      </div>

      <!-- Right: Recent Execution Runs -->
      <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col space-y-4">
        <div class="flex items-center justify-between pb-3 border-b border-slate-800">
          <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
            <i class="fa-solid fa-list-check text-indigo-400"></i>
            <span>Recent Executions</span>
          </h2>
          <span class="text-xs text-slate-400" id="runs-badge">Latest runs</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-xs">
            <thead class="text-slate-400 uppercase tracking-wider bg-slate-800/40 border-b border-slate-800">
              <tr>
                <th class="py-2.5 px-3">Run ID</th>
                <th class="py-2.5 px-3">Workflow</th>
                <th class="py-2.5 px-3">Status</th>
                <th class="py-2.5 px-3">Trigger</th>
                <th class="py-2.5 px-3">Duration</th>
                <th class="py-2.5 px-3">Action</th>
              </tr>
            </thead>
            <tbody id="runs-table-body" class="divide-y divide-slate-800/60">
              <tr>
                <td colspan="6" class="text-center py-8 text-slate-400 italic">No execution runs recorded yet.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </div>

    <!-- Run Detail Modal / Inspector -->
    <div id="detail-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-slate-900 border border-slate-700 w-full max-w-4xl rounded-2xl p-6 shadow-2xl flex flex-col max-h-[90vh]">
        <div class="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 class="text-base font-bold text-white flex items-center space-x-2">
              <span id="modal-run-id" class="text-sky-400">Run Details</span>
              <span id="modal-status-badge"></span>
            </h3>
            <p id="modal-workflow-info" class="text-xs text-slate-400 mt-1"></p>
          </div>
          <button onclick="closeModal()" class="text-slate-400 hover:text-white p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition">
            <i class="fa-solid fa-xmark text-base"></i>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Step Execution Tree</h4>
          <div id="modal-steps-container" class="space-y-3"></div>
        </div>
      </div>
    </div>

  </main>

  <footer class="bg-slate-900 border-t border-slate-800 py-4 px-6 text-center text-xs text-slate-400">
    FlowForge Engine v0.1.0 • Built with Python, AsyncIO & FastAPI
  </footer>

  <script>
    async function fetchData(url) {
      const res = await fetch(url);
      return res.json();
    }

    function statusBadge(status) {
      if (status === 'success') {
        return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-950 text-emerald-400 border border-emerald-800"><i class="fa-solid fa-check mr-1 text-[9px]"></i> Success</span>';
      } else if (status === 'failed') {
        return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-rose-950 text-rose-400 border border-rose-800"><i class="fa-solid fa-xmark mr-1 text-[9px]"></i> Failed</span>';
      } else if (status === 'running') {
        return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-sky-950 text-sky-400 border border-sky-800"><i class="fa-solid fa-spinner fa-spin mr-1 text-[9px]"></i> Running</span>';
      } else if (status === 'skipped') {
        return '<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400 border border-slate-700">Skipped</span>';
      }
      return `<span class="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium bg-amber-950 text-amber-400 border border-amber-800">${status}</span>`;
    }

    async function triggerWorkflow(wfId) {
      try {
        const btn = document.getElementById(`btn-run-${wfId}`);
        if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Running...';
        const res = await fetch(`/api/v1/workflows/${wfId}/run`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ payload: { source: 'dashboard_ui' } })
        });
        await refreshData();
      } catch (err) {
        alert('Failed triggering workflow: ' + err);
      }
    }

    async function inspectRun(runId) {
      const run = await fetchData(`/api/v1/runs/${runId}`);
      document.getElementById('modal-run-id').innerText = run.run_id;
      document.getElementById('modal-status-badge').innerHTML = statusBadge(run.status);
      document.getElementById('modal-workflow-info').innerText = 
        `Workflow: ${run.workflow_id} | Trigger: ${run.trigger_type} | Duration: ${run.duration_ms || 0}ms`;

      const stepsContainer = document.getElementById('modal-steps-container');
      stepsContainer.innerHTML = '';

      const steps = Object.values(run.step_runs || {});
      if (steps.length === 0) {
        stepsContainer.innerHTML = '<p class="text-xs text-slate-500 italic">No steps recorded in this run.</p>';
      } else {
        steps.forEach(st => {
          const div = document.createElement('div');
          div.className = 'bg-slate-800/80 border border-slate-700 rounded-lg p-3 space-y-2';
          div.innerHTML = `
            <div class="flex items-center justify-between">
              <div class="flex items-center space-x-2">
                <span class="font-bold text-white text-xs">${st.step_id}</span>
                ${statusBadge(st.status)}
              </div>
              <span class="text-slate-400 text-[11px]">Attempt: ${st.attempt} • ${st.duration_ms ? st.duration_ms.toFixed(1) + 'ms' : '-'}</span>
            </div>
            ${st.error ? `<div class="bg-rose-950/60 border border-rose-800/80 rounded p-2 text-rose-300 text-xs font-mono">${st.error}</div>` : ''}
            ${st.output_data ? `<details class="text-[11px]"><summary class="text-slate-400 cursor-pointer hover:text-slate-300 font-medium">Output JSON</summary><pre class="bg-slate-900 rounded p-2 mt-1 text-slate-300 overflow-x-auto max-h-40 font-mono">${JSON.stringify(st.output_data, null, 2)}</pre></details>` : ''}
            ${st.logs && st.logs.length ? `<details class="text-[11px]"><summary class="text-slate-400 cursor-pointer hover:text-slate-300 font-medium">Logs (${st.logs.length})</summary><ul class="list-disc list-inside bg-slate-900/60 rounded p-2 mt-1 text-slate-400 font-mono text-[10px] space-y-0.5">${st.logs.map(l => `<li>${l}</li>`).join('')}</ul></details>` : ''}
          `;
          stepsContainer.appendChild(div);
        });
      }

      const modal = document.getElementById('detail-modal');
      modal.classList.remove('hidden');
      modal.classList.add('flex');
    }

    function closeModal() {
      const modal = document.getElementById('detail-modal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }

    async function refreshData() {
      try {
        const [workflows, runs] = await Promise.all([
          fetchData('/api/v1/workflows'),
          fetchData('/api/v1/runs?limit=30')
        ]);

        document.getElementById('metric-workflows').innerText = workflows.length;
        document.getElementById('metric-runs').innerText = runs.length;
        document.getElementById('workflow-badge').innerText = `${workflows.length} workflows`;

        let successful = runs.filter(r => r.status === 'success').length;
        let rate = runs.length > 0 ? ((successful / runs.length) * 100).toFixed(0) + '%' : '100%';
        document.getElementById('metric-success').innerText = rate;

        let totalMs = runs.reduce((acc, r) => acc + (r.duration_ms || 0), 0);
        let avgMs = runs.length > 0 ? (totalMs / runs.length).toFixed(0) + ' ms' : '0 ms';
        document.getElementById('metric-duration').innerText = avgMs;

        // Render Workflows
        const wfList = document.getElementById('workflows-list');
        if (workflows.length === 0) {
          wfList.innerHTML = '<p class="text-xs text-slate-500 italic text-center py-4">No workflows found.</p>';
        } else {
          wfList.innerHTML = workflows.map(wf => `
            <div class="bg-slate-800/60 border border-slate-700/80 rounded-lg p-3 hover:border-slate-600 transition flex items-center justify-between">
              <div>
                <h4 class="text-xs font-bold text-white flex items-center space-x-1.5">
                  <span>${wf.name}</span>
                  <span class="text-[10px] text-slate-400 bg-slate-700/80 px-1.5 py-0.2 rounded font-mono">${wf.id}</span>
                </h4>
                <p class="text-[11px] text-slate-400 mt-0.5 line-clamp-1">${wf.description || 'No description'}</p>
                <div class="text-[10px] text-slate-500 mt-1 flex space-x-2">
                  <span><i class="fa-solid fa-list-ol mr-1"></i>${wf.steps.length} steps</span>
                  <span><i class="fa-solid fa-bolt mr-1"></i>${wf.triggers ? wf.triggers.length : 0} triggers</span>
                </div>
              </div>
              <button id="btn-run-${wf.id}" onclick="triggerWorkflow('${wf.id}')" class="px-2.5 py-1 text-xs bg-sky-600 hover:bg-sky-500 text-white rounded font-medium shadow-sm transition flex items-center space-x-1">
                <i class="fa-solid fa-play text-[10px]"></i> <span>Run</span>
              </button>
            </div>
          `).join('');
        }

        // Render Runs Table
        const tbody = document.getElementById('runs-table-body');
        if (runs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-500 italic">No runs executed yet.</td></tr>';
        } else {
          tbody.innerHTML = runs.map(r => `
            <tr class="hover:bg-slate-800/40 transition">
              <td class="py-2.5 px-3 font-mono text-[11px] text-sky-400 font-semibold">${r.run_id}</td>
              <td class="py-2.5 px-3 text-slate-300 font-medium">${r.workflow_id}</td>
              <td class="py-2.5 px-3">${statusBadge(r.status)}</td>
              <td class="py-2.5 px-3 font-mono text-[11px] text-slate-400">${r.trigger_type}</td>
              <td class="py-2.5 px-3 font-mono text-[11px] text-slate-300">${r.duration_ms ? r.duration_ms.toFixed(1) + ' ms' : '-'}</td>
              <td class="py-2.5 px-3">
                <button onclick="inspectRun('${r.run_id}')" class="text-sky-400 hover:text-sky-300 font-medium text-xs hover:underline flex items-center space-x-1">
                  <i class="fa-regular fa-eye"></i> <span>Inspect</span>
                </button>
              </td>
            </tr>
          `).join('');
        }

      } catch (e) {
        console.error('Failed refreshing dashboard:', e);
      }
    }

    refreshData();
    setInterval(refreshData, 5000); // 5s auto-refresh
  </script>
</body>
</html>"""
