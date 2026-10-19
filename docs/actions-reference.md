# Actions Reference 📖

FlowForge comes with a comprehensive suite of built-in actions for common infrastructure, data engineering, and automation workflows.

---

## 1. `http` - Asynchronous REST API Calls
Executes non-blocking HTTP requests with connection pooling and timeouts.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `url` | string | Yes | Request target URL (supports templating) |
| `method` | string | No | HTTP verb: `GET`, `POST`, `PUT`, `DELETE`, `PATCH` (default: `GET`) |
| `headers` | dict | No | HTTP request headers |
| `params` | dict | No | Query parameters |
| `json` | any | No | JSON serializable body payload |
| `timeout` | float | No | Request timeout in seconds (default: 30.0) |
| `expected_status` | list/int | No | Acceptable HTTP status codes (default: `[200, 201, 202, 204]`) |

**Output Variables:**
- `steps.<id>.output.status_code` (int)
- `steps.<id>.output.json` (dict/list)
- `steps.<id>.output.text` (str)
- `steps.<id>.output.elapsed_ms` (float)

---

## 2. `shell` - Subprocess Commands & Scripts
Executes async terminal commands with exit-code tracking and stdout/stderr capture.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `command` | string | Yes | Shell command or bash script to run |
| `cwd` | string | No | Working directory for the process |
| `env` | dict | No | Extra environment variables |
| `timeout` | float | No | Maximum execution time in seconds |
| `fail_on_error` | bool | No | Raise error if exit code != 0 (default: `true`) |

**Output Variables:**
- `steps.<id>.output.stdout` (str)
- `steps.<id>.output.stderr` (str)
- `steps.<id>.output.exit_code` (int)
- `steps.<id>.output.elapsed_ms` (float)

---

## 3. `transform` - Data Projection & Manipulation
Evaluates and projects structured data, list slices, and dictionaries.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `value` | any | No | Direct value or template mapping to return |
| `items` | list | No | Array of items to filter or slice |
| `limit` | int | No | Maximum elements to slice from `items` |

---

## 4. `file` - Local File System Operations
Reads, writes, appends, and manages local files.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `operation` | string | Yes | `read`, `write`, `append`, `exists`, `delete`, `list` |
| `path` | string | Yes | Path to the target file or directory |
| `content` | any | No | Content to write or append (auto JSON formatted if object) |
| `encoding` | string | No | File encoding (default: `utf-8`) |

---

## 5. `sql` - SQLite Database Queries
Executes SQL queries against SQLite databases with parameter binding.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | SQL statement to execute |
| `database` | string | No | Path to SQLite database file (default: `flowforge.db`) |
| `params` | list | No | Positional query parameter bindings |
| `fetch` | bool | No | If `true`, returns query results as a list of dictionaries (default: `true`) |

**Output Variables:**
- `steps.<id>.output.rows` (list of dicts)
- `steps.<id>.output.row_count` (int)

---

## 6. `notify` - Discord & Slack Webhooks
Dispatches formatted notifications to Discord or Slack channels.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `webhook_url` | string | Yes | Incoming webhook URL |
| `channel` | string | No | `discord`, `slack`, or `generic` (default: `generic`) |
| `title` | string | No | Notification title |
| `message` | string | Yes | Body message text or markdown |
| `level` | string | No | Alert level: `info`, `success`, `warning`, `error` |

---

## 7. `llm` - AI Decision & Extraction Node
Invokes OpenAI-compatible endpoints (OpenAI, Ollama, LocalAI, vLLM).

| Parameter | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | Yes | Input prompt for the AI model |
| `model` | string | No | Model name (default: `gpt-4o-mini`) |
| `system` | string | No | System instruction prompt |
| `temperature` | float | No | Sampling temperature (default: `0.2`) |
| `base_url` | string | No | Custom API base URL (default: OpenAI or `$OPENAI_BASE_URL`) |
| `json_mode` | bool | No | Request structured JSON response |

---

## 8. Custom Action Development

Adding custom actions in Python is trivial:

```python
from flowforge.actions.base import BaseAction, ActionResult, ActionContext, register_action
from typing import Dict, Any

@register_action("custom_greet")
class CustomGreetAction(BaseAction):
    name = "custom_greet"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        user = params.get("user", "Developer")
        return ActionResult(
            success=True,
            output={"greeting": f"Hello, {user}!"},
            logs=[f"Greeted {user}"]
        )
```
