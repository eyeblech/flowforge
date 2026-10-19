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
