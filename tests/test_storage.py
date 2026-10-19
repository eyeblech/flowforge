"""Tests for persistence storage backends (SQLite and Memory)."""

import pytest
from pathlib import Path
from flowforge.core.models import (
    StepDefinition,
    StepRun,
    StepStatus,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStatus,
)
from flowforge.storage.memory import MemoryStorage
from flowforge.storage.sqlite import SQLiteStorage


@pytest.fixture(params=["memory", "sqlite"])
def storage(request, tmp_path: Path):
    if request.param == "memory":
        return MemoryStorage()
    else:
        db_path = tmp_path / "test_flowforge.db"
        return SQLiteStorage(db_path)


def test_storage_workflow_crud(storage):
    wf = WorkflowDefinition(
        id="wf_crud_test",
        name="CRUD Test Workflow",
        steps=[StepDefinition(id="step1", action="shell")],
    )

    storage.save_workflow(wf)
    retrieved = storage.get_workflow("wf_crud_test")
    assert retrieved is not None
    assert retrieved.id == "wf_crud_test"
    assert retrieved.name == "CRUD Test Workflow"

    workflows = storage.list_workflows()
    assert any(w.id == "wf_crud_test" for w in workflows)


def test_storage_run_crud(storage):
    run = WorkflowRun(
        run_id="run_001",
        workflow_id="wf_crud_test",
        status=WorkflowStatus.RUNNING,
        trigger_type="manual",
    )
    storage.create_run(run)

    step_run = StepRun(
        step_id="step1",
        run_id="run_001",
        status=StepStatus.SUCCESS,
        output_data={"answer": 42},
    )
    storage.save_step_run(step_run)

    run.status = WorkflowStatus.SUCCESS
    run.mark_success()
    storage.update_run(run)

    retrieved_run = storage.get_run("run_001")
    assert retrieved_run is not None
    assert retrieved_run.status == WorkflowStatus.SUCCESS
    assert "step1" in retrieved_run.step_runs
    assert retrieved_run.step_runs["step1"].output_data == {"answer": 42}

    runs = storage.list_runs(workflow_id="wf_crud_test", limit=10)
    assert len(runs) >= 1
    assert runs[0].run_id == "run_001"
