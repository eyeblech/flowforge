"""FlowForge Studio Dashboard HTML, CSS & JavaScript single-page application."""

def get_dashboard_html() -> str:
    """Return modern, self-contained HTML/CSS/JS dashboard for FlowForge."""
    return """<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FlowForge Orchestration Studio</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <script>
    tailwind.config = {
      darkMode: 'class',
      theme: {
        extend: {
          colors: {
            brand: { 50: '#f0f9ff', 500: '#0284c7', 600: '#0369a1', 900: '#0c4a6e' },
            darkbg: '#0b0f19',
            surface: '#151d30',
            card: '#1e293b',
            border: '#334155',
          }
        }
      }
    };
    mermaid.initialize({
      startOnLoad: false,
      theme: 'dark',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis'
      }
    });
  </script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0b0f19; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    pre, code, textarea.code-font { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
    .mermaid svg { max-width: 100% !important; height: auto !important; }
    /* Custom scrollbars */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #475569; }
  </style>
</head>
<body class="text-slate-200 min-h-screen flex flex-col bg-[#0b0f19]">

  <!-- Header Navbar -->
  <header class="bg-slate-900/95 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between sticky top-0 z-50 backdrop-blur shadow-lg">
    <div class="flex items-center space-x-6">
      <div class="flex items-center space-x-3 cursor-pointer" onclick="switchTab('dashboard')">
        <div class="bg-gradient-to-tr from-sky-500 via-indigo-500 to-purple-600 w-10 h-10 rounded-xl flex items-center justify-center shadow-lg shadow-sky-500/25">
          <i class="fa-solid fa-bolt text-white text-xl animate-pulse"></i>
        </div>
        <div>
          <div class="flex items-center space-x-2">
            <h1 class="text-lg font-black text-white tracking-wide">FlowForge</h1>
            <span class="text-[10px] font-mono bg-sky-500/10 text-sky-400 border border-sky-500/20 px-1.5 py-0.5 rounded">v0.1.0</span>
          </div>
          <p class="text-[11px] text-slate-400">Developer-First Async Task Orchestration Engine</p>
        </div>
      </div>

      <!-- Navigation Tabs -->
      <nav class="hidden md:flex items-center space-x-1 pl-4 border-l border-slate-800">
        <button id="nav-dashboard" onclick="switchTab('dashboard')" class="nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg transition flex items-center space-x-2 bg-sky-600 text-white shadow-sm">
          <i class="fa-solid fa-chart-line"></i>
          <span>Dashboard & Runs</span>
        </button>
        <button id="nav-visualizer" onclick="switchTab('visualizer')" class="nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center space-x-2">
          <i class="fa-solid fa-diagram-project"></i>
          <span>DAG Visualizer</span>
        </button>
        <button id="nav-studio" onclick="switchTab('studio')" class="nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center space-x-2">
          <i class="fa-solid fa-code"></i>
          <span>YAML Studio & Runner</span>
        </button>
        <button id="nav-webhooks" onclick="switchTab('webhooks')" class="nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center space-x-2">
          <i class="fa-solid fa-satellite-dish"></i>
          <span>Webhooks & API</span>
        </button>
      </nav>
    </div>

    <!-- Right Controls -->
    <div class="flex items-center space-x-3">
      <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-400 border border-emerald-800 shadow-sm">
        <span class="w-2 h-2 mr-2 bg-emerald-400 rounded-full animate-ping"></span> Async Engine Active
      </span>
      <button onclick="refreshData()" title="Refresh Data" class="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium rounded-lg border border-slate-700 transition flex items-center space-x-1.5 shadow-sm">
        <i class="fa-solid fa-rotate-right" id="refresh-icon"></i> <span>Refresh</span>
      </button>
      <a href="/docs" target="_blank" class="px-2.5 py-1.5 text-xs text-slate-400 hover:text-sky-400 rounded-lg bg-slate-800/50 hover:bg-slate-800 border border-slate-700/60 transition" title="Swagger API Docs">
        <i class="fa-solid fa-book-open mr-1"></i> API Docs
      </a>
    </div>
  </header>

  <!-- Main Container -->
  <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">

    <!-- TAB 1: DASHBOARD & RUNS -->
    <section id="tab-dashboard" class="space-y-6">
      <!-- Metrics Cards -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Registered Workflows</span>
            <div class="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-400 flex items-center justify-center">
              <i class="fa-solid fa-diagram-project text-sm"></i>
            </div>
          </div>
          <div class="text-3xl font-extrabold text-white mt-3" id="metric-workflows">0</div>
          <div class="text-xs text-slate-400 mt-1 flex items-center">
            <span class="text-sky-400 font-medium mr-1.5">● Ready</span> In memory & database
          </div>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Execution Runs</span>
            <div class="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <i class="fa-solid fa-play text-sm"></i>
            </div>
          </div>
          <div class="text-3xl font-extrabold text-white mt-3" id="metric-runs">0</div>
          <div class="text-xs text-slate-400 mt-1 flex items-center">
            <span class="text-indigo-400 font-medium mr-1.5">● Microsecond</span> SQLite checkpointing
          </div>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Success Rate</span>
            <div class="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <i class="fa-solid fa-circle-check text-sm"></i>
            </div>
          </div>
          <div class="text-3xl font-extrabold text-emerald-400 mt-3" id="metric-success">100%</div>
          <div class="text-xs text-slate-400 mt-1 flex items-center">
            <span class="text-emerald-400 font-medium mr-1.5">● Reliable</span> Auto-retry backoff
          </div>
        </div>

        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm hover:border-slate-700 transition">
          <div class="flex items-center justify-between text-slate-400 text-xs font-semibold uppercase tracking-wider">
            <span>Avg Run Latency</span>
            <div class="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
              <i class="fa-solid fa-bolt text-sm"></i>
            </div>
          </div>
          <div class="text-3xl font-extrabold text-amber-300 mt-3" id="metric-duration">0 ms</div>
          <div class="text-xs text-slate-400 mt-1 flex items-center">
            <span class="text-amber-400 font-medium mr-1.5">● Fast</span> Zero cluster overhead
          </div>
        </div>
      </div>

      <!-- Two Column Layout: Workflows and Recent Executions -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Left: Workflows -->
        <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
              <i class="fa-solid fa-network-wired text-sky-400"></i>
              <span>Loaded Pipelines</span>
            </h2>
            <span class="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono" id="workflow-badge">0</span>
          </div>
          <div id="workflows-list" class="space-y-3 overflow-y-auto max-h-[560px] pr-1">
            <p class="text-xs text-slate-400 italic text-center py-6">Loading workflows...</p>
          </div>
        </div>

        <!-- Right: Recent Executions -->
        <div class="lg:col-span-2 bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col space-y-4">
          <div class="flex items-center justify-between pb-3 border-b border-slate-800">
            <div class="flex items-center space-x-2">
              <h2 class="text-sm font-bold text-white uppercase tracking-wider flex items-center space-x-2">
                <i class="fa-solid fa-list-check text-indigo-400"></i>
                <span>Execution Timeline</span>
              </h2>
              <span class="text-[11px] text-slate-500">(Auto-refreshes every 5s)</span>
            </div>
            <span class="text-xs text-slate-400" id="runs-badge">Latest runs</span>
          </div>

          <div class="overflow-x-auto rounded-xl border border-slate-800/80">
            <table class="w-full text-left text-xs">
              <thead class="text-slate-400 uppercase tracking-wider bg-slate-800/60 border-b border-slate-800">
                <tr>
                  <th class="py-3 px-3.5">Run ID</th>
                  <th class="py-3 px-3.5">Workflow</th>
                  <th class="py-3 px-3.5">Status</th>
                  <th class="py-3 px-3.5">Trigger</th>
                  <th class="py-3 px-3.5">Duration</th>
                  <th class="py-3 px-3.5 text-right">Actions</th>
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
    </section>

    <!-- TAB 2: DAG VISUALIZER -->
    <section id="tab-visualizer" class="hidden space-y-6">
      <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm flex flex-col space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 class="text-base font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-diagram-project text-sky-400"></i>
              <span>Directed Acyclic Graph (DAG) Visualizer</span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Explore pipeline topologies, dependencies, and parallel fan-out concurrency.</p>
          </div>

          <div class="flex items-center space-x-3">
            <label class="text-xs text-slate-400 font-medium">Select Workflow:</label>
            <select id="dag-workflow-select" onchange="loadWorkflowDAG(this.value)" class="bg-slate-800 border border-slate-700 text-white text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-sky-500 outline-none">
              <option value="">Select pipeline...</option>
            </select>
            <button onclick="reloadCurrentDAG()" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 transition flex items-center space-x-1">
              <i class="fa-solid fa-rotate-right"></i> <span>Re-render</span>
            </button>
          </div>
        </div>

        <!-- DAG Metadata Strip -->
        <div id="dag-metadata-strip" class="hidden grid grid-cols-1 md:grid-cols-3 gap-3 p-3 bg-slate-800/40 rounded-xl border border-slate-800 text-xs">
          <div>
            <span class="text-slate-400 block text-[11px] uppercase">Workflow ID</span>
            <span class="text-white font-mono font-semibold" id="dag-meta-id">-</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px] uppercase">Root Concurrent Steps</span>
            <span class="text-sky-400 font-mono" id="dag-meta-roots">-</span>
          </div>
          <div>
            <span class="text-slate-400 block text-[11px] uppercase">Topological Execution Order</span>
            <span class="text-emerald-400 font-mono text-[11px]" id="dag-meta-order">-</span>
          </div>
        </div>

        <!-- Mermaid Graph Canvas -->
        <div class="bg-slate-950/60 rounded-xl p-6 border border-slate-800/80 min-h-[420px] flex items-center justify-center overflow-x-auto relative">
          <div id="mermaid-graph-container" class="w-full flex justify-center">
            <div class="text-center py-12 text-slate-500">
              <i class="fa-solid fa-bezier-curve text-4xl mb-3 text-slate-600 block"></i>
              Select a workflow from the dropdown above to render its interactive DAG diagram.
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 3: YAML STUDIO & PLAYGROUND -->
    <section id="tab-studio" class="hidden space-y-6">
      <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
        <div class="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 class="text-base font-bold text-white flex items-center space-x-2">
              <i class="fa-solid fa-code text-purple-400"></i>
              <span>Interactive Workflow Studio & Runner</span>
            </h2>
            <p class="text-xs text-slate-400 mt-0.5">Write or customize declarative YAML pipelines, validate cycle-free DAGs, and execute instantly.</p>
          </div>

          <div class="flex flex-wrap items-center gap-2">
            <!-- Template Loader -->
            <select id="studio-template-select" onchange="loadTemplateIntoStudio(this.value)" class="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:ring-1 focus:ring-purple-500 outline-none">
              <option value="">Load Template Workflow...</option>
            </select>

            <button onclick="validateStudioYAML()" class="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs rounded-lg border border-slate-700 transition font-medium flex items-center space-x-1.5">
              <i class="fa-solid fa-check text-sky-400"></i> <span>Validate DAG</span>
            </button>

            <button onclick="runStudioYAML()" id="btn-studio-run" class="px-4 py-1.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs rounded-lg font-bold transition shadow-lg shadow-emerald-500/20 flex items-center space-x-1.5">
              <i class="fa-solid fa-play"></i> <span>Execute Pipeline</span>
            </button>
          </div>
        </div>

        <!-- Studio Split Layout: Editor on Left, Live Output/DAG on Right -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Editor Box -->
          <div class="flex flex-col space-y-2">
            <div class="flex items-center justify-between text-xs text-slate-400 px-1">
              <span class="font-medium"><i class="fa-regular fa-file-code mr-1"></i> workflow.yaml</span>
              <span class="text-[11px] text-slate-500">YAML Schema Validated</span>
            </div>
            <textarea id="studio-yaml-editor" spellcheck="false" class="code-font w-full h-[480px] bg-slate-950 border border-slate-800 rounded-xl p-4 text-xs text-slate-200 leading-relaxed focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none" placeholder="Paste or edit workflow YAML here..."></textarea>
          </div>

          <!-- Output & Execution Results Panel -->
          <div class="flex flex-col space-y-2">
            <!-- Sub-tabs: Results / Rendered DAG -->
            <div class="flex items-center justify-between border-b border-slate-800 pb-2">
              <div class="flex items-center space-x-2 text-xs font-semibold">
                <button id="studio-tab-output-btn" onclick="switchStudioSubtab('output')" class="px-3 py-1 bg-slate-800 text-white rounded-md">Live Output</button>
                <button id="studio-tab-dag-btn" onclick="switchStudioSubtab('dag')" class="px-3 py-1 text-slate-400 hover:text-white rounded-md">Rendered DAG</button>
              </div>
              <span id="studio-status-indicator" class="text-xs text-slate-500 font-mono">Idle</span>
            </div>

            <!-- Subtab Panel: Output -->
            <div id="studio-panel-output" class="bg-slate-950 rounded-xl p-4 border border-slate-800 h-[480px] overflow-y-auto space-y-3">
              <div id="studio-feedback-banner"></div>
              <div id="studio-run-results" class="space-y-3">
                <p class="text-xs text-slate-500 italic text-center py-16">
                  Click <strong class="text-emerald-400">Execute Pipeline</strong> above to run this workflow and view microsecond step results and logs.
                </p>
              </div>
            </div>

            <!-- Subtab Panel: DAG -->
            <div id="studio-panel-dag" class="hidden bg-slate-950 rounded-xl p-4 border border-slate-800 h-[480px] overflow-auto flex items-center justify-center">
              <div id="studio-mermaid-container" class="w-full flex justify-center">
                <p class="text-xs text-slate-500 italic text-center">Click Validate DAG to generate visual graph.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- TAB 4: WEBHOOKS & API SANDBOX -->
    <section id="tab-webhooks" class="hidden space-y-6">
      <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-sm space-y-4">
        <div class="pb-4 border-b border-slate-800">
          <h2 class="text-base font-bold text-white flex items-center space-x-2">
            <i class="fa-solid fa-satellite-dish text-teal-400"></i>
            <span>Webhook Ingestion & REST API Sandbox</span>
          </h2>
          <p class="text-xs text-slate-400 mt-0.5">Test inbound event payloads, bearer token verification, and automated event triggers.</p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div class="space-y-4">
            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Target Webhook Pipeline</label>
              <select id="webhook-target-select" onchange="updateWebhookSnippet()" class="w-full bg-slate-800 border border-slate-700 text-white text-xs rounded-lg p-2.5 outline-none focus:ring-1 focus:ring-teal-500">
                <option value="webhook_pipeline">Webhook Event Ingestion Pipeline (webhook_pipeline)</option>
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Secret Auth Token (X-FlowForge-Token / Bearer)</label>
              <input id="webhook-token-input" type="text" value="secret_flowforge_token_xyz" class="w-full bg-slate-950 border border-slate-800 text-white text-xs rounded-lg p-2.5 font-mono outline-none focus:ring-1 focus:ring-teal-500" placeholder="secret_token...">
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">JSON Event Payload</label>
              <textarea id="webhook-payload-input" spellcheck="false" class="code-font w-full h-40 bg-slate-950 border border-slate-800 text-white text-xs rounded-lg p-3 font-mono outline-none resize-none focus:ring-1 focus:ring-teal-500">{
  "event": "alert.critical",
  "system": "edge-cluster-04",
  "metric": "disk_utilization",
  "value": 94.2,
  "severity": "CRITICAL",
  "timestamp": "2026-10-20T21:00:00Z"
}</textarea>
            </div>

            <button onclick="sendWebhookTest()" id="btn-send-webhook" class="w-full py-2.5 bg-gradient-to-r from-teal-600 to-sky-600 hover:from-teal-500 hover:to-sky-500 text-white text-xs font-bold rounded-lg transition shadow-md shadow-teal-500/20 flex items-center justify-center space-x-2">
              <i class="fa-solid fa-paper-plane"></i> <span>Send Webhook Event</span>
            </button>
          </div>

          <!-- Webhook Response & cURL Info -->
          <div class="space-y-4">
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs font-semibold uppercase tracking-wider text-slate-400">Equivalent cURL Request</label>
                <button onclick="copyWebhookCurl()" class="text-[11px] text-teal-400 hover:text-teal-300 font-mono"><i class="fa-regular fa-copy mr-1"></i>Copy</button>
              </div>
              <pre id="webhook-curl-snippet" class="bg-slate-950 border border-slate-800 rounded-lg p-3 text-[11px] text-slate-300 font-mono overflow-x-auto whitespace-pre-wrap"></pre>
            </div>

            <div>
              <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Server Response</label>
              <pre id="webhook-response-box" class="bg-slate-950 border border-slate-800 rounded-lg p-3 text-[11px] text-slate-400 font-mono h-48 overflow-y-auto">Waiting for webhook trigger...</pre>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Run Detail Modal / Inspector -->
    <div id="detail-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-slate-900 border border-slate-700 w-full max-w-4xl rounded-2xl p-6 shadow-2xl flex flex-col max-h-[90vh]">
        <div class="flex items-center justify-between pb-4 border-b border-slate-800">
          <div>
            <h3 class="text-base font-bold text-white flex items-center space-x-2">
              <span id="modal-run-id" class="text-sky-400 font-mono">Run Details</span>
              <span id="modal-status-badge"></span>
            </h3>
            <p id="modal-workflow-info" class="text-xs text-slate-400 mt-1"></p>
          </div>
          <button onclick="closeModal()" class="text-slate-400 hover:text-white p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition">
            <i class="fa-solid fa-xmark text-base"></i>
          </button>
        </div>

        <div class="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
          <!-- Live Run Graph -->
          <div class="bg-slate-950/80 border border-slate-800 rounded-xl p-4">
            <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center space-x-2">
              <i class="fa-solid fa-diagram-project text-sky-400"></i>
              <span>Execution State Graph</span>
            </h4>
            <div id="modal-mermaid-graph" class="w-full flex justify-center overflow-x-auto"></div>
          </div>

          <h4 class="text-xs font-semibold uppercase tracking-wider text-slate-400">Step Execution Tree</h4>
          <div id="modal-steps-container" class="space-y-3"></div>
        </div>
      </div>
    </div>

  </main>

  <footer class="bg-slate-900 border-t border-slate-800 py-4 px-6 text-center text-xs text-slate-400">
    FlowForge Engine v0.1.0 • Built with Python, AsyncIO, SQLite WAL & FastAPI
  </footer>

  <script>
    let globalWorkflows = [];
    let globalTemplates = [];
    let currentDAGWorkflowId = '';

    // Switch Top Navigation Tabs
    function switchTab(tabId) {
      ['dashboard', 'visualizer', 'studio', 'webhooks'].forEach(t => {
        const section = document.getElementById(`tab-${t}`);
        const navBtn = document.getElementById(`nav-${t}`);
        if (t === tabId) {
          section.classList.remove('hidden');
          navBtn.className = 'nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg transition flex items-center space-x-2 bg-sky-600 text-white shadow-sm';
        } else {
          section.classList.add('hidden');
          navBtn.className = 'nav-tab px-3 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition flex items-center space-x-2';
        }
      });

      if (tabId === 'visualizer' && !currentDAGWorkflowId && globalWorkflows.length > 0) {
        loadWorkflowDAG(globalWorkflows[0].id);
      }
    }

    function switchStudioSubtab(sub) {
      const outputPanel = document.getElementById('studio-panel-output');
      const dagPanel = document.getElementById('studio-panel-dag');
      const outputBtn = document.getElementById('studio-tab-output-btn');
      const dagBtn = document.getElementById('studio-tab-dag-btn');

      if (sub === 'output') {
        outputPanel.classList.remove('hidden');
        dagPanel.classList.add('hidden');
        outputBtn.className = 'px-3 py-1 bg-slate-800 text-white rounded-md';
        dagBtn.className = 'px-3 py-1 text-slate-400 hover:text-white rounded-md';
      } else {
        outputPanel.classList.add('hidden');
        dagPanel.classList.remove('hidden');
        dagBtn.className = 'px-3 py-1 bg-slate-800 text-white rounded-md';
        outputBtn.className = 'px-3 py-1 text-slate-400 hover:text-white rounded-md';
        validateStudioYAML();
      }
    }

    async function fetchData(url) {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
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
        const run = await res.json();
        await refreshData();
        inspectRun(run.run_id);
      } catch (err) {
        alert('Failed triggering workflow: ' + err);
      }
    }

    async function inspectRun(runId) {
      try {
        const run = await fetchData(`/api/v1/runs/${runId}`);
        document.getElementById('modal-run-id').innerText = run.run_id;
        document.getElementById('modal-status-badge').innerHTML = statusBadge(run.status);
        document.getElementById('modal-workflow-info').innerText = 
          `Workflow: ${run.workflow_id} | Trigger: ${run.trigger_type} | Duration: ${run.duration_ms ? run.duration_ms.toFixed(1) : 0}ms`;

        // Render Run Status Graph
        try {
          const dagData = await fetchData(`/api/v1/workflows/${run.workflow_id}/dag?run_id=${run.run_id}`);
          const graphContainer = document.getElementById('modal-mermaid-graph');
          const renderId = 'modal-graph-' + Date.now();
          const { svg } = await mermaid.render(renderId, dagData.mermaid);
          graphContainer.innerHTML = svg;
        } catch (e) {
          console.error("Failed rendering run graph:", e);
        }

        const stepsContainer = document.getElementById('modal-steps-container');
        stepsContainer.innerHTML = '';

        const steps = Object.values(run.step_runs || {});
        if (steps.length === 0) {
          stepsContainer.innerHTML = '<p class="text-xs text-slate-500 italic">No steps recorded in this run.</p>';
        } else {
          steps.forEach(st => {
            const div = document.createElement('div');
            div.className = 'bg-slate-800/80 border border-slate-700 rounded-xl p-3.5 space-y-2';
            div.innerHTML = `
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <span class="font-bold text-white text-xs font-mono">${st.step_id}</span>
                  ${statusBadge(st.status)}
                </div>
                <span class="text-slate-400 text-[11px] font-mono">Attempt: ${st.attempt} • ${st.duration_ms ? st.duration_ms.toFixed(1) + 'ms' : '-'}</span>
              </div>
              ${st.error ? `<div class="bg-rose-950/60 border border-rose-800/80 rounded-lg p-2.5 text-rose-300 text-xs font-mono">${st.error}</div>` : ''}
              ${st.output_data ? `<details class="text-[11px]"><summary class="text-slate-400 cursor-pointer hover:text-slate-300 font-medium">Output JSON</summary><pre class="bg-slate-900/90 rounded-lg p-2.5 mt-1 text-slate-300 overflow-x-auto max-h-48 font-mono">${JSON.stringify(st.output_data, null, 2)}</pre></details>` : ''}
              ${st.logs && st.logs.length ? `<details class="text-[11px]"><summary class="text-slate-400 cursor-pointer hover:text-slate-300 font-medium">Execution Logs (${st.logs.length})</summary><ul class="list-disc list-inside bg-slate-900/60 rounded-lg p-2.5 mt-1 text-slate-400 font-mono text-[10px] space-y-1">${st.logs.map(l => `<li>${l}</li>`).join('')}</ul></details>` : ''}
            `;
            stepsContainer.appendChild(div);
          });
        }

        const modal = document.getElementById('detail-modal');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      } catch (err) {
        alert('Failed fetching run details: ' + err);
      }
    }

    function closeModal() {
      const modal = document.getElementById('detail-modal');
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    }

    // DAG Visualizer Functions
    async function loadWorkflowDAG(wfId) {
      if (!wfId) return;
      currentDAGWorkflowId = wfId;
      const select = document.getElementById('dag-workflow-select');
      select.value = wfId;

      try {
        const data = await fetchData(`/api/v1/workflows/${wfId}/dag`);
        const strip = document.getElementById('dag-metadata-strip');
        strip.classList.remove('hidden');
        document.getElementById('dag-meta-id').innerText = data.workflow_id;
        document.getElementById('dag-meta-roots').innerText = (data.root_steps || []).join(', ') || 'None';
        document.getElementById('dag-meta-order').innerText = (data.execution_order || []).join(' → ');

        const container = document.getElementById('mermaid-graph-container');
        const renderId = 'dag-render-' + Date.now();
        const { svg } = await mermaid.render(renderId, data.mermaid);
        container.innerHTML = svg;
      } catch (err) {
        document.getElementById('mermaid-graph-container').innerHTML = 
          `<div class="text-rose-400 text-xs font-mono p-4 bg-rose-950/40 rounded-lg border border-rose-800">Failed rendering DAG: ${err.message}</div>`;
      }
    }

    function reloadCurrentDAG() {
      if (currentDAGWorkflowId) loadWorkflowDAG(currentDAGWorkflowId);
    }

    // Studio & Playground Functions
    async function loadTemplateIntoStudio(templateId) {
      if (!templateId) return;
      const t = globalTemplates.find(x => x.id === templateId);
      if (t) {
        document.getElementById('studio-yaml-editor').value = t.yaml;
        validateStudioYAML();
      }
    }

    async function validateStudioYAML() {
      const yaml = document.getElementById('studio-yaml-editor').value.trim();
      const banner = document.getElementById('studio-feedback-banner');
      const indicator = document.getElementById('studio-status-indicator');

      if (!yaml) {
        banner.innerHTML = '<div class="text-amber-400 text-xs font-mono p-3 bg-amber-950/40 rounded-lg border border-amber-800">Editor is empty. Select a template or write YAML.</div>';
        return;
      }

      indicator.innerText = 'Validating...';
      try {
        const res = await fetch('/api/v1/workflows/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ yaml_content: yaml })
        });
        const data = await res.json();

        if (data.valid) {
          indicator.innerText = 'Valid DAG';
          indicator.className = 'text-xs text-emerald-400 font-mono';
          banner.innerHTML = `
            <div class="bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs rounded-lg p-3">
              <div class="font-bold flex items-center space-x-1.5 mb-1">
                <i class="fa-solid fa-circle-check text-emerald-400"></i>
                <span>Workflow Validated: ${data.name} (${data.id})</span>
              </div>
              <div class="text-[11px] text-slate-300">
                Steps: <strong>${data.step_count}</strong> • Concurrency Roots: <strong>${(data.root_steps || []).join(', ')}</strong><br/>
                Topological Order: <span class="font-mono text-emerald-400">${(data.execution_order || []).join(' → ')}</span>
              </div>
            </div>
          `;

          // Render in studio DAG panel if present
          if (data.mermaid) {
            const container = document.getElementById('studio-mermaid-container');
            const renderId = 'studio-mermaid-' + Date.now();
            const { svg } = await mermaid.render(renderId, data.mermaid);
            container.innerHTML = svg;
          }
        } else {
          indicator.innerText = 'Validation Error';
          indicator.className = 'text-xs text-rose-400 font-mono';
          banner.innerHTML = `
            <div class="bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg p-3">
              <div class="font-bold flex items-center space-x-1.5 mb-1">
                <i class="fa-solid fa-triangle-exclamation text-rose-400"></i>
                <span>DAG / Syntax Error</span>
              </div>
              <div class="text-[11px] font-mono whitespace-pre-wrap">${data.error}</div>
            </div>
          `;
        }
      } catch (err) {
        indicator.innerText = 'Error';
        banner.innerHTML = `<div class="bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg p-3 font-mono">${err.message}</div>`;
      }
    }

    async function runStudioYAML() {
      const yaml = document.getElementById('studio-yaml-editor').value.trim();
      const resultsContainer = document.getElementById('studio-run-results');
      const btn = document.getElementById('btn-studio-run');
      const indicator = document.getElementById('studio-status-indicator');

      if (!yaml) {
        alert('Please write or select a workflow before executing.');
        return;
      }

      switchStudioSubtab('output');
      btn.disabled = true;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> <span>Executing...</span>';
      indicator.innerText = 'Executing...';
      resultsContainer.innerHTML = '<p class="text-xs text-sky-400 font-mono text-center py-12"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Engine running workflow steps in parallel...</p>';

      try {
        const res = await fetch('/api/v1/workflows/run-custom', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ yaml_content: yaml, payload: { source: 'studio_runner' } })
        });
        const run = await res.json();

        indicator.innerText = `Run: ${run.status}`;
        indicator.className = run.status === 'success' ? 'text-xs text-emerald-400 font-mono' : 'text-xs text-rose-400 font-mono';

        let stepsHtml = '';
        const steps = Object.values(run.step_runs || {});
        steps.forEach(st => {
          stepsHtml += `
            <div class="bg-slate-900 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs">
              <div class="flex items-center justify-between">
                <span class="font-bold font-mono text-white">${st.step_id}</span>
                ${statusBadge(st.status)}
              </div>
              <div class="text-[11px] text-slate-400 font-mono">Attempt: ${st.attempt} • ${st.duration_ms ? st.duration_ms.toFixed(1) + 'ms' : '-'}</div>
              ${st.error ? `<div class="bg-rose-950/70 border border-rose-800/80 rounded p-2 text-rose-300 text-[11px] font-mono">${st.error}</div>` : ''}
              ${st.output_data ? `<details class="text-[11px]"><summary class="text-slate-400 cursor-pointer hover:text-slate-300">Output JSON</summary><pre class="bg-slate-950 rounded p-2 mt-1 text-slate-300 overflow-x-auto max-h-36 font-mono text-[10px]">${JSON.stringify(st.output_data, null, 2)}</pre></details>` : ''}
            </div>
          `;
        });

        resultsContainer.innerHTML = `
          <div class="p-3 bg-slate-900/90 rounded-lg border border-slate-800 flex items-center justify-between text-xs">
            <div>
              <span class="font-mono text-sky-400 font-bold">${run.run_id}</span>
              <span class="text-slate-400 ml-2">Total: <strong>${run.duration_ms ? run.duration_ms.toFixed(1) : 0}ms</strong></span>
            </div>
            ${statusBadge(run.status)}
          </div>
          <div class="space-y-2">
            ${stepsHtml}
          </div>
        `;

        await refreshData();
      } catch (err) {
        resultsContainer.innerHTML = `<div class="bg-rose-950/60 border border-rose-800 text-rose-300 text-xs rounded-lg p-3 font-mono">Execution failed: ${err.message}</div>`;
      } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> <span>Execute Pipeline</span>';
      }
    }

    // Webhooks Sandbox Functions
    function updateWebhookSnippet() {
      const wfId = document.getElementById('webhook-target-select').value;
      const token = document.getElementById('webhook-token-input').value;
      const host = window.location.origin;
      const snippet = `curl -X POST "${host}/api/v1/webhooks/${wfId}" \\
  -H "Content-Type: application/json" \\
  -H "X-FlowForge-Token: ${token}" \\
  -d '{"event":"alert.critical","system":"edge-cluster-04","value":94.2}'`;
      document.getElementById('webhook-curl-snippet').innerText = snippet;
    }

    function copyWebhookCurl() {
      const text = document.getElementById('webhook-curl-snippet').innerText;
      navigator.clipboard.writeText(text);
      alert('cURL command copied to clipboard!');
    }

    async function sendWebhookTest() {
      const wfId = document.getElementById('webhook-target-select').value;
      const token = document.getElementById('webhook-token-input').value;
      const payloadStr = document.getElementById('webhook-payload-input').value;
      const respBox = document.getElementById('webhook-response-box');

      respBox.innerText = 'Sending webhook request...';
      try {
        let payload = JSON.parse(payloadStr);
        const res = await fetch(`/api/v1/webhooks/${wfId}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-FlowForge-Token': token
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        respBox.innerText = `Status: ${res.status} ${res.statusText}\n\n` + JSON.stringify(data, null, 2);
        await refreshData();
      } catch (err) {
        respBox.innerText = 'Error: ' + err.message;
      }
    }

    // Global Refresh Data
    async function refreshData() {
      const icon = document.getElementById('refresh-icon');
      if (icon) icon.classList.add('fa-spin');

      try {
        const [workflows, runs, templates] = await Promise.all([
          fetchData('/api/v1/workflows'),
          fetchData('/api/v1/runs?limit=30'),
          fetchData('/api/v1/templates')
        ]);

        globalWorkflows = workflows;
        globalTemplates = templates;

        document.getElementById('metric-workflows').innerText = workflows.length;
        document.getElementById('metric-runs').innerText = runs.length;
        document.getElementById('workflow-badge').innerText = `${workflows.length} loaded`;

        let successful = runs.filter(r => r.status === 'success').length;
        let rate = runs.length > 0 ? ((successful / runs.length) * 100).toFixed(0) + '%' : '100%';
        document.getElementById('metric-success').innerText = rate;

        let totalMs = runs.reduce((acc, r) => acc + (r.duration_ms || 0), 0);
        let avgMs = runs.length > 0 ? (totalMs / runs.length).toFixed(0) + ' ms' : '0 ms';
        document.getElementById('metric-duration').innerText = avgMs;

        // Render Workflows in List
        const wfList = document.getElementById('workflows-list');
        if (workflows.length === 0) {
          wfList.innerHTML = '<p class="text-xs text-slate-500 italic text-center py-4">No workflows found.</p>';
        } else {
          wfList.innerHTML = workflows.map(wf => `
            <div class="bg-slate-800/60 border border-slate-700/80 rounded-xl p-3.5 hover:border-slate-600 transition flex items-center justify-between">
              <div class="space-y-1">
                <h4 class="text-xs font-bold text-white flex items-center space-x-1.5">
                  <span>${wf.name}</span>
                  <span class="text-[10px] text-slate-400 bg-slate-700/80 px-1.5 py-0.2 rounded font-mono">${wf.id}</span>
                </h4>
                <p class="text-[11px] text-slate-400 line-clamp-1">${wf.description || 'No description'}</p>
                <div class="text-[10px] text-slate-500 flex space-x-3">
                  <span><i class="fa-solid fa-list-ol mr-1"></i>${wf.steps.length} steps</span>
                  <span><i class="fa-solid fa-bolt mr-1"></i>${wf.triggers ? wf.triggers.length : 0} triggers</span>
                </div>
              </div>
              <div class="flex items-center space-x-1.5">
                <button onclick="switchTab('visualizer'); loadWorkflowDAG('${wf.id}')" title="View DAG" class="px-2 py-1 text-xs bg-slate-700 hover:bg-slate-600 text-slate-300 rounded font-medium transition">
                  <i class="fa-solid fa-diagram-project"></i>
                </button>
                <button id="btn-run-${wf.id}" onclick="triggerWorkflow('${wf.id}')" class="px-2.5 py-1 text-xs bg-sky-600 hover:bg-sky-500 text-white rounded font-medium shadow-sm transition flex items-center space-x-1">
                  <i class="fa-solid fa-play text-[10px]"></i> <span>Run</span>
                </button>
              </div>
            </div>
          `).join('');
        }

        // Populate DAG Select Dropdown
        const dagSelect = document.getElementById('dag-workflow-select');
        const currentSel = dagSelect.value;
        dagSelect.innerHTML = '<option value="">Select pipeline...</option>' + 
          workflows.map(w => `<option value="${w.id}">${w.name} (${w.id})</option>`).join('');
        if (currentSel) dagSelect.value = currentSel;

        // Populate Template Select in Studio
        const tplSelect = document.getElementById('studio-template-select');
        const curTpl = tplSelect.value;
        tplSelect.innerHTML = '<option value="">Load Template Workflow...</option>' + 
          templates.map(t => `<option value="${t.id}">${t.name} (${t.step_count} steps)</option>`).join('');
        if (curTpl) tplSelect.value = curTpl;

        // Populate Webhook Targets
        const whSelect = document.getElementById('webhook-target-select');
        const whWorkflows = workflows.filter(w => (w.triggers || []).some(t => t.type === 'webhook'));
        if (whWorkflows.length > 0) {
          whSelect.innerHTML = whWorkflows.map(w => `<option value="${w.id}">${w.name} (${w.id})</option>`).join('');
        }
        updateWebhookSnippet();

        // If studio editor is empty, prefill with first template
        const editor = document.getElementById('studio-yaml-editor');
        if (!editor.value && templates.length > 0) {
          editor.value = templates[0].yaml;
          tplSelect.value = templates[0].id;
        }

        // Render Runs Table
        const tbody = document.getElementById('runs-table-body');
        if (runs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-500 italic">No runs executed yet.</td></tr>';
        } else {
          tbody.innerHTML = runs.map(r => `
            <tr class="hover:bg-slate-800/40 transition">
              <td class="py-3 px-3.5 font-mono text-[11px] text-sky-400 font-semibold">${r.run_id}</td>
              <td class="py-3 px-3.5 text-slate-300 font-medium">${r.workflow_id}</td>
              <td class="py-3 px-3.5">${statusBadge(r.status)}</td>
              <td class="py-3 px-3.5 font-mono text-[11px] text-slate-400">${r.trigger_type}</td>
              <td class="py-3 px-3.5 font-mono text-[11px] text-slate-300">${r.duration_ms ? r.duration_ms.toFixed(1) + ' ms' : '-'}</td>
              <td class="py-3 px-3.5 text-right">
                <button onclick="inspectRun('${r.run_id}')" class="text-sky-400 hover:text-sky-300 font-medium text-xs hover:underline inline-flex items-center space-x-1">
                  <i class="fa-regular fa-eye"></i> <span>Inspect</span>
                </button>
              </td>
            </tr>
          `).join('');
        }

      } catch (e) {
        console.error('Failed refreshing dashboard:', e);
      } finally {
        if (icon) icon.classList.remove('fa-spin');
      }
    }

    // Initial load
    refreshData();
    setInterval(refreshData, 5000); // 5s auto-refresh
  </script>
</body>
</html>"""
