# Getting Started with FlowForge ⚡

FlowForge is a lightweight, resilient, developer-first workflow automation and task orchestration engine for Python.

---

## 1. Installation

### From Source
```bash
git clone https://github.com/your-username/flowforge.git
cd flowforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## 2. Quickstart: Your First Workflow

Create a file named `my_workflow.yaml`:

```yaml
id: hello_automation
name: Hello Automation Pipeline
version: "1.0"
description: My first FlowForge pipeline

steps:
  - id: fetch_ip
    name: Fetch Public IP Info
    action: http
    with:
      url: "https://httpbin.org/ip"
      expected_status: [200]

  - id: format_message
    name: Format IP Output
    action: transform
    depends_on: [fetch_ip]
    with:
      value:
        origin_ip: "{{ steps.fetch_ip.output.json.origin }}"
        timestamp: "{{ now().isoformat() }}"

  - id: save_result
    name: Save to Local File
    action: file
    depends_on: [format_message]
    with:
      operation: write
      path: "./output/my_ip.json"
      content: "{{ steps.format_message.output | to_json }}"
```

### Validate Syntax & DAG
```bash
flowforge validate my_workflow.yaml
```

### Visualize Dependency Tree
```bash
flowforge tree my_workflow.yaml
```

### Run Locally
```bash
flowforge run my_workflow.yaml
```

---

## 3. Webhook Triggers & Web Dashboard

Launch the embedded FlowForge Studio and webhook listener:

```bash
flowforge serve --workflows-dir ./examples --port 8000
```

1. Open your browser to `http://localhost:8000`.
2. Inspect registered workflows and historical runs.
3. Trigger any workflow manually with custom JSON input.
4. Send an incoming HTTP webhook:

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/webhook_pipeline \
  -H "Content-Type: application/json" \
  -H "X-FlowForge-Token: secret123" \
  -d '{"action": "deploy_completed", "sender": {"login": "octocat"}}'
```

---

## 4. Cron Scheduling

Add a cron trigger to any workflow definition:

```yaml
triggers:
  - type: cron
    config:
      expression: "*/15 * * * *"  # Runs every 15 minutes
```

When you start `flowforge serve`, the background cron scheduler registers and executes the workflow automatically according to the cron schedule.
