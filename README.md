<div align="center">

```
  ╔═╗┬  ┌─┐┬ ┬╔═╗┌─┐┬─┐┌─┐┌─┐
  ╠╣ │  │ ││││╠╣ │ │├┬┘│ ┬├┤ 
  ╚  ┴─┘└─┘└┴┘╚  └─┘┴└─└─┘└─┘
```

# FlowForge ⚡

### A lightweight, resilient, developer-first workflow automation and task orchestration engine for Python.

[![CI](https://github.com/your-username/flowforge/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/flowforge/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Architecture: AsyncIO](https://img.shields.io/badge/engine-asyncio-purple.svg)](https://docs.python.org/3/library/asyncio.html)

[Features](#-key-features) • [Quickstart](#-quickstart) • [Architecture](#-architecture) • [Example Workflows](#-ready-to-run-examples) • [Web Studio](#-web-studio--api) • [CLI Reference](#-cli-commands) • [Docs](docs/)

</div>

---

## 💡 Why FlowForge?

Modern orchestration tools like Airflow or Temporal are powerful, but they often require massive distributed infrastructure, JVM dependencies, Redis/Kafka brokers, and complex Kubernetes setups just to run simple, reliable automation pipelines.

**FlowForge** fills the gap: it delivers the **power of a DAG-based orchestration engine** with the **simplicity of a single Python package**.

- **Zero Heavyweight Infrastructure**: No Redis, RabbitMQ, or Celery workers required. Runs locally or in a single tiny container.
- **Async-Native DAG Execution**: Uses Kahn's algorithm for topological sorting and cycle detection, executing independent pipeline branches concurrently via Python `asyncio`.
- **Fault-Tolerant by Default**: Exponential backoff retries with jitter, per-step timeouts, and failure boundary isolation (`continue_on_error`).
- **SQLite WAL Checkpointing**: Complete execution history, step status, inputs, and outputs are persisted to SQLite with WAL mode for microsecond overhead.
- **Batteries-Included Actions**: Out-of-the-box support for REST APIs (`http`), bash scripts (`shell`), file I/O (`file`), SQL databases (`sql`), Slack/Discord webhooks (`notify`), and AI nodes (`llm`).
- **Multi-Interface**: Beautiful **Rich terminal CLI**, interactive **Dark Mode Web Dashboard**, and programmatic Python API.

---

## ⚡ Key Features

| Capability | Description |
|---|---|
| **DAG Scheduling** | Multi-branch fan-out and fan-in dependency resolution with cycle prevention. |
| **Expression Engine** | Safe Jinja2 templating with dot notation (`{{ steps.fetch.output.json.data }}`). |
| **Resilient Retries** | Configurable exponential backoff, jitter, and timeout per task. |
| **Trigger Ecosystem** | Cron scheduler, HTTP webhooks with HMAC verification, directory file watcher. |
| **Extensible Actions** | Easily register custom Python task actions with `@register_action`. |
| **Telemetry & Observability** | Real-time event bus, execution duration metrics, and audit logging. |
| **Web Dashboard** | Embedded FastAPI web dashboard with run inspector and manual execution trigger. |

---

## 🏗 Architecture

```
                    ┌────────────────────────────┐
                    │      Trigger Layer         │
                    │  (CLI, Webhook, Cron, Watch)│
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │      Workflow Parser       │
                    │   (YAML/JSON Validation)   │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
                    ┌────────────────────────────┐
                    │        DAG Engine          │
                    │  (Kahn's Cycle Detection)  │
                    └─────────────┬──────────────┘
                                  │
                                  ▼
      ┌────────────────────────────────────────────────────────┐
      │               Async Workflow Engine                     │
      │                                                        │
      │  ┌───────────────────┐        ┌─────────────────────┐  │
      │  │ Step Scheduler    │        │ Semaphore           │  │
      │  │ (Parallel Tasks)  │◄──────►│ (Concurrency Cap)   │  │
      │  └─────────┬─────────┘        └─────────────────────┘  │
      │            │                                           │
      │            ▼                                           │
      │  ┌───────────────────┐        ┌─────────────────────┐  │
      │  │ Expression Engine │        │ Action Registry     │  │
      │  │ (Jinja2 Templates)│◄──────►│ (HTTP, Shell, File, │  │
      │  └─────────┬─────────┘        │  SQL, Notify, LLM)  │  │
      │            │                  └─────────────────────┘  │
      │            ▼                                           │
      │  ┌───────────────────┐                                 │
      │  │ Retry Policy Loop │                                 │
      │  │ (Exponential+Jitter)                                │
      │  └───────────────────┘                                 │
      └───────────────────────────┬────────────────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 ▼                                 ▼
    ┌──────────────────────────┐     ┌───────────────────────────┐
    │   SQLite WAL Storage     │     │       Event Bus           │
    │  (Runs, Steps, Telemetry)│     │  (CLI Live TUI & Server)  │
    └──────────────────────────┘     └───────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/your-username/flowforge.git
cd flowforge

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install FlowForge
pip install -e .
```

### 2. Run an Example Pipeline

FlowForge includes pre-built production workflows in [`examples/`](examples/):

```bash
# Run the parallel DAG fan-out pipeline
flowforge run examples/05_parallel_dag_fanout.yaml
```

**Terminal Output:**
```
╭──────────────────────────────────────────────────────────────────────────────╮
│  ╔═╗┬  ┌─┐┬ ┬╔═╗┌─┐┬─┐┌─┐┌─┐                                                 │
│  ╠╣ │  │ ││││╠╣ │ │├┬┘│ ┬├┤                                                  │
│  ╚  ┴─┘└─┘└┴┘╚  └─┘┴└─└─┘└─┘                                                 │
│  Developer-first async workflow automation engine                            │
╰──────────────────────────────────────────────────────────────────────────────╯
Loaded workflow: Parallel DAG Fan-Out & Aggregation (6 steps)
Starting execution pipeline...
  ▶ Running step: init_pipeline
  ✔ Completed step: init_pipeline
  ▶ Running step: worker_shard_beta
  ▶ Running step: worker_shard_alpha
  ▶ Running step: worker_shard_gamma
  ✔ Completed step: worker_shard_beta
  ✔ Completed step: worker_shard_alpha
  ✔ Completed step: worker_shard_gamma
  ▶ Running step: aggregate_shards
  ✔ Completed step: aggregate_shards
  ▶ Running step: output_batch_summary
  ✔ Completed step: output_batch_summary

Execution Summary: Parallel DAG Fan-Out & Aggregation (run_ac2f4d07eeab)        
┏━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Step ID         ┃ Action    ┃  Status   ┃ Attempt ┃ Duration ┃ Error / Notes ┃
┡━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ init_pipeline   │ transform │ ● SUCCESS │    1    │    4.1ms │               │
│ worker_shard_b… │ shell     │ ● SUCCESS │    1    │  204.6ms │               │
│ worker_shard_a… │ shell     │ ● SUCCESS │    1    │  204.1ms │               │
│ worker_shard_g… │ shell     │ ● SUCCESS │    1    │  204.0ms │               │
│ aggregate_shar… │ transform │ ● SUCCESS │    1    │    4.7ms │               │
│ output_batch_s… │ file      │ ● SUCCESS │    1    │    2.2ms │               │
└─────────────────┴───────────┴───────────┴─────────┴──────────┴───────────────┘

╭─ Run Result ─────────────────────────────────────────────────────────────────╮
│ Status: ● SUCCESS  │  Total Duration: 223.80ms  │  Trigger: cli              │
╰──────────────────────────────────────────────────────────────────────────────╯
```

---

## 📝 Defining Workflows (YAML Specification)

Workflows are clean, declarative YAML documents:

```yaml
id: github_release_tracker
name: GitHub Release Tracker & Alert
version: "1.0"
description: Fetches latest GitHub releases and archives release notes

env:
  TARGET_REPO: "pallets/flask"

triggers:
  - type: cron
    config:
      expression: "0 */6 * * *"  # Run every 6 hours

steps:
  - id: fetch_latest_release
    name: Fetch Latest Release
    action: http
    retry:
      max_attempts: 3
      initial_delay: 2.0
      backoff_multiplier: 2.0
    with:
      url: "https://api.github.com/repos/{{ env.TARGET_REPO }}/releases/latest"
      expected_status: [200]

  - id: format_release_notes
    name: Extract Version & Notes
    action: transform
    depends_on: [fetch_latest_release]
    with:
      value:
        tag: "{{ steps.fetch_latest_release.output.json.tag_name }}"
        author: "{{ steps.fetch_latest_release.output.json.author.login }}"
        notes: "{{ steps.fetch_latest_release.output.json.body }}"

  - id: save_release_file
    name: Save Release Markdown
    action: file
    depends_on: [format_release_notes]
    with:
      operation: write
      path: "./output/releases/{{ steps.format_release_notes.output.tag }}.md"
      content: |
        # Flask Release: {{ steps.format_release_notes.output.tag }}
        Released by @{{ steps.format_release_notes.output.author }}
        
        {{ steps.format_release_notes.output.notes }}
```

---

## 🌐 Web Studio & API

Start the self-hosted Web Dashboard, REST API, and Webhook Receiver:

```bash
flowforge serve --workflows-dir ./examples --port 8000
```

- **Interactive Studio UI**: Navigate to `http://localhost:8000` to view real-time execution telemetry, inspect step outputs, and trigger workflows on-demand.
- **REST Endpoints**:
  - `GET /api/v1/health` - System health and registered workflow count.
  - `GET /api/v1/workflows` - List all registered workflows.
  - `POST /api/v1/workflows/{id}/run` - Manually trigger execution with payload.
  - `GET /api/v1/runs` - Query historical execution logs.
  - `POST /api/v1/webhooks/{id}` - Ingest authenticated incoming webhooks.

---

## 🛠 Ready-to-Run Examples

The repository contains 6 production-ready automation workflows in [`examples/`](examples/):

1. **`01_github_release_monitor.yaml`**: Polls the GitHub API, parses release tags, and generates local markdown documentation.
2. **`02_system_health_watchdog.yaml`**: Diagnoses disk space, RAM, and uptime; records continuous telemetry.
3. **`03_api_data_etl.yaml`**: Extracts data from REST APIs, normalizes payloads, and loads records into SQLite via SQL queries.
4. **`04_ai_incident_summarizer.yaml`**: Synthesizes root-cause analysis and automated remediation plans for server errors.
5. **`05_parallel_dag_fanout.yaml`**: Demonstrates barrier synchronization where 3 parallel workers run concurrently before a join step.
6. **`06_webhook_pipeline.yaml`**: Ingests authenticated webhooks (with token validation) and dispatches formatted alerts.

---

## 💻 CLI Commands

```bash
# Validate workflow DAG syntax and detect circular dependencies
flowforge validate examples/01_github_release_monitor.yaml

# Render terminal dependency tree
flowforge tree examples/05_parallel_dag_fanout.yaml

# Execute a workflow locally
flowforge run examples/03_api_data_etl.yaml

# List historical execution runs from SQLite
flowforge runs list

# Inspect detailed step logs and outputs of a specific run
flowforge runs get <run_id>

# Scaffold a new automation project
flowforge init my_project
```

---

## 🐳 Docker Deployment

Run the complete FlowForge container with Docker Compose:

```bash
docker compose up -d
```

The Web Dashboard and Webhook listener will be live on `http://localhost:8000`.

---

## 🧪 Testing

FlowForge maintains a comprehensive test suite covering models, expressions, DAG cycle detection, storage engines, actions, runner retries, REST endpoints, and CLI commands.

```bash
# Run pytest with async support
pytest -v
```

---

## 📄 License

FlowForge is open-source software licensed under the [MIT License](LICENSE).
