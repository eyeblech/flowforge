# FlowForge Architecture & Design

FlowForge is architected around a modular, asynchronous execution engine built with Python 3.10+, `asyncio`, Pydantic v2, and SQLite.

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

## Key Subsystems

### 1. Directed Acyclic Graph (DAG) Engine
- Uses **Kahn’s Algorithm** for topological sorting and cycle detection.
- Discovers independent root steps and begins executing them concurrently.
- As steps finish, downstream dependent steps whose prerequisites are fulfilled are automatically dispatched to the event loop.

### 2. Expression & Template Evaluator
- Embedded Jinja2 sandbox with dot-accessible dictionary traversal (`{{ steps.my_step.output.data }}`).
- Automatic type preservation: if an expression resolves to an integer, dictionary, or boolean, it remains in its native Python type.
- Built-in utility filters: `to_json`, `from_json`, `upper`, `lower`, `trim`, `regex_search`, and `now()`.

### 3. Fault Tolerance & Resiliency
- Configurable **Exponential Backoff with Jitter** retry policies.
- Per-step timeout enforcement via `asyncio.wait_for`.
- Granular error boundary handling (`continue_on_error: true` for non-critical steps).

### 4. Zero-Config SQLite WAL Storage
- All workflow definitions, runs, and step outputs are persisted to SQLite with `PRAGMA journal_mode=WAL` for concurrent write performance.
- Full audit history and execution metrics.
