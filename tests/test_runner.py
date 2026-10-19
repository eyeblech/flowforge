"""Tests for the async WorkflowEngine execution, retries, and conditions."""

import pytest
from flowforge.core.models import (
    RetryPolicy,
    StepDefinition,
    StepStatus,
    WorkflowDefinition,
    WorkflowStatus,
)
from flowforge.engine.runner import WorkflowEngine
from flowforge.storage.memory import MemoryStorage


@pytest.mark.asyncio
async def test_linear_workflow_execution(sample_linear_workflow: WorkflowDefinition):
    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(sample_linear_workflow)

    assert run.status == WorkflowStatus.SUCCESS
    assert "step_one" in run.step_runs
    assert "step_two" in run.step_runs
    assert run.step_runs["step_one"].status == StepStatus.SUCCESS
    assert run.step_runs["step_two"].status == StepStatus.SUCCESS
    assert run.step_runs["step_two"].output_data == {"echo": "hello from step one"}


@pytest.mark.asyncio
async def test_branching_parallel_execution(sample_branching_workflow: WorkflowDefinition):
    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(sample_branching_workflow)

    assert run.status == WorkflowStatus.SUCCESS
    assert len(run.step_runs) == 4
    for sid in ["root", "branch_a", "branch_b", "join"]:
        assert run.step_runs[sid].status == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_condition_skipping():
    wf = WorkflowDefinition(
        id="cond_wf",
        name="Conditional Workflow",
        steps=[
            StepDefinition(
                id="check",
                action="transform",
                **{"with": {"value": {"is_admin": False}}},
            ),
            StepDefinition(
                id="admin_only_step",
                action="transform",
                depends_on=["check"],
                when="{{ steps.check.output.is_admin == true }}",
                **{"with": {"value": {"secret": "supersecret"}}},
            ),
            StepDefinition(
                id="final_step",
                action="transform",
                depends_on=["check"],
                **{"with": {"value": {"done": True}}},
            ),
        ],
    )

    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(wf)

    assert run.status == WorkflowStatus.SUCCESS
    assert run.step_runs["check"].status == StepStatus.SUCCESS
    assert run.step_runs["admin_only_step"].status == StepStatus.SKIPPED
    assert run.step_runs["final_step"].status == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_step_failure_and_cascade_skip():
    wf = WorkflowDefinition(
        id="fail_wf",
        name="Failing Workflow",
        steps=[
            StepDefinition(
                id="failing_step",
                action="shell",
                **{"with": {"command": "exit 1", "fail_on_error": True}},
            ),
            StepDefinition(
                id="downstream_step",
                action="transform",
                depends_on=["failing_step"],
                **{"with": {"value": {"data": 123}}},
            ),
        ],
    )

    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(wf)

    assert run.status == WorkflowStatus.FAILED
    assert run.step_runs["failing_step"].status == StepStatus.FAILED
    assert run.step_runs["downstream_step"].status == StepStatus.SKIPPED


@pytest.mark.asyncio
async def test_continue_on_error():
    wf = WorkflowDefinition(
        id="continue_wf",
        name="Continue On Error Workflow",
        steps=[
            StepDefinition(
                id="non_critical_step",
                action="shell",
                continue_on_error=True,
                **{"with": {"command": "exit 1", "fail_on_error": True}},
            ),
            StepDefinition(
                id="downstream_step",
                action="transform",
                depends_on=["non_critical_step"],
                continue_on_error=True,
                **{"with": {"value": {"data": 123}}},
            ),
        ],
    )

    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(wf)

    assert run.status == WorkflowStatus.PARTIALLY_FAILED
    assert run.step_runs["non_critical_step"].status == StepStatus.FAILED
    assert run.step_runs["downstream_step"].status == StepStatus.SUCCESS


@pytest.mark.asyncio
async def test_step_retry_policy():
    # Use shell script with temporary file to fail on attempt 1 and succeed on attempt 2
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        flag_file = tmp.name

    wf = WorkflowDefinition(
        id="retry_wf",
        name="Retry Workflow",
        steps=[
            StepDefinition(
                id="retry_step",
                action="shell",
                retry=RetryPolicy(max_attempts=3, initial_delay=0.05, jitter=False),
                **{
                    "with": {
                        "command": f"""
if [ -f '{flag_file}.attempted' ]; then
    echo "succeeded on retry"
    exit 0
else
    touch '{flag_file}.attempted'
    exit 1
fi
""",
                        "fail_on_error": True,
                    }
                },
            ),
        ],
    )

    engine = WorkflowEngine(storage=MemoryStorage())
    run = await engine.execute(wf)

    assert run.status == WorkflowStatus.SUCCESS
    assert run.step_runs["retry_step"].status == StepStatus.SUCCESS
    assert run.step_runs["retry_step"].attempt == 2
