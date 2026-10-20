"""Tests for FastAPI endpoints, webhook receiver, and web dashboard."""

import pytest
from fastapi.testclient import TestClient

from flowforge.core.models import (
    StepDefinition,
    TriggerDefinition,
    TriggerType,
    WorkflowDefinition,
)
from flowforge.server.app import create_app
from flowforge.storage.memory import MemoryStorage


@pytest.fixture
def test_client():
    storage = MemoryStorage()
    wf = WorkflowDefinition(
        id="api_test_wf",
        name="API Test Workflow",
        triggers=[
            TriggerDefinition(
                type=TriggerType.WEBHOOK,
                config={"secret_token": "valid_token_123"},
            )
        ],
        steps=[
            StepDefinition(
                id="ping",
                action="transform",
                **{"with": {"value": {"status": "pong"}}},
            )
        ],
    )
    storage.save_workflow(wf)
    app = create_app(storage=storage)
    app.state.workflows["api_test_wf"] = wf

    with TestClient(app) as client:
        yield client


def test_health_endpoint(test_client: TestClient):
    res = test_client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_list_workflows_endpoint(test_client: TestClient):
    res = test_client.get("/api/v1/workflows")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["id"] == "api_test_wf"


def test_trigger_workflow_endpoint(test_client: TestClient):
    res = test_client.post(
        "/api/v1/workflows/api_test_wf/run",
        json={"payload": {"source": "unit_test"}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == "api_test_wf"
    assert data["status"] == "success"


def test_webhook_unauthorized(test_client: TestClient):
    res = test_client.post(
        "/api/v1/webhooks/api_test_wf",
        json={"msg": "unauthorized attempt"},
        headers={"X-FlowForge-Token": "wrong_token"},
    )
    assert res.status_code == 401


def test_webhook_authorized(test_client: TestClient):
    res = test_client.post(
        "/api/v1/webhooks/api_test_wf",
        json={"event": "ping"},
        headers={"X-FlowForge-Token": "valid_token_123"},
    )
    assert res.status_code == 202
    data = res.json()
    assert "run_id" in data
    assert data["status"] == "success"


def test_dashboard_html_endpoint(test_client: TestClient):
    res = test_client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "FlowForge" in res.text


def test_templates_endpoint(test_client: TestClient):
    res = test_client.get("/api/v1/templates")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_validate_workflow_endpoint(test_client: TestClient):
    valid_yaml = """
id: sample_val
name: Valid Workflow
steps:
  - id: step_a
    action: transform
    with:
      value: 1
  - id: step_b
    action: transform
    depends_on: [step_a]
    with:
      value: 2
"""
    res = test_client.post("/api/v1/workflows/validate", json={"yaml_content": valid_yaml})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["id"] == "sample_val"
    assert data["step_count"] == 2
    assert "mermaid" in data
    assert data["execution_order"] == ["step_a", "step_b"]

    invalid_yaml = """
id: sample_invalid
name: Invalid Cyclic Workflow
steps:
  - id: step_x
    action: transform
    depends_on: [step_y]
    with:
      value: 1
  - id: step_y
    action: transform
    depends_on: [step_x]
    with:
      value: 2
"""
    res = test_client.post("/api/v1/workflows/validate", json={"yaml_content": invalid_yaml})
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is False
    assert "Cyclic" in data["error"] or "cycle" in data["error"].lower()


def test_workflow_dag_endpoint(test_client: TestClient):
    res = test_client.get("/api/v1/workflows/api_test_wf/dag")
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == "api_test_wf"
    assert "mermaid" in data
    assert "graph TD" in data["mermaid"]
    assert "ping" in data["mermaid"]


def test_run_custom_workflow_endpoint(test_client: TestClient):
    custom_yaml = """
id: custom_studio_wf
name: Custom Studio Pipeline
steps:
  - id: quick_step
    action: transform
    with:
      value:
        hello: "world"
"""
    res = test_client.post(
        "/api/v1/workflows/run-custom",
        json={"yaml_content": custom_yaml, "payload": {"foo": "bar"}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["workflow_id"] == "custom_studio_wf"
    assert data["status"] == "success"
    assert "quick_step" in data["step_runs"]


def test_demo_mode_blocks_custom_shell():
    storage = MemoryStorage()
    app = create_app(storage=storage, demo_mode=True)
    with TestClient(app) as client:
        # Health check includes demo_mode
        health_res = client.get("/api/v1/health")
        assert health_res.status_code == 200
        assert health_res.json()["demo_mode"] is True

        # Custom workflow with shell step must be rejected
        dangerous_yaml = """
id: test_malicious_yaml
name: Attempt Custom Shell
steps:
  - id: exec_shell
    action: shell
    with:
      command: "echo test"
"""
        res = client.post(
            "/api/v1/workflows/run-custom",
            json={"yaml_content": dangerous_yaml},
        )
        assert res.status_code == 403
        assert "disabled in public demo sandbox" in res.json()["detail"]

        # Custom workflow with safe transform must succeed
        safe_yaml = """
id: test_safe_custom
name: Safe Transform
steps:
  - id: safe_calc
    action: transform
    with:
      value:
        ok: true
"""
        res_safe = client.post(
            "/api/v1/workflows/run-custom",
            json={"yaml_content": safe_yaml},
        )
        assert res_safe.status_code == 200
        assert res_safe.json()["status"] == "success"

        # Dashboard shows demo badge
        dash_res = client.get("/")
        assert dash_res.status_code == 200
        assert "Demo Sandbox" in dash_res.text



