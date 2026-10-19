"""Tests for FlowForge core data models and state transitions."""

import pytest
from datetime import datetime, timezone
from flowforge.core.models import (
    RetryPolicy,
    StepDefinition,
    StepRun,
    StepStatus,
    TriggerDefinition,
    TriggerType,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStatus,
)


def test_retry_policy_defaults():
    policy = RetryPolicy()
    assert policy.max_attempts == 3
    assert policy.initial_delay == 1.0
    assert policy.backoff_multiplier == 2.0
    assert policy.jitter is True


def test_step_run_lifecycle():
    step_run = StepRun(step_id="step1", run_id="run_123")
    assert step_run.status == StepStatus.PENDING

    step_run.mark_started()
    assert step_run.status == StepStatus.RUNNING
    assert step_run.started_at is not None

    step_run.mark_success(output={"res": 42})
    assert step_run.status == StepStatus.SUCCESS
    assert step_run.output_data == {"res": 42}
    assert step_run.duration_ms is not None
    assert step_run.duration_ms >= 0


def test_step_run_failure():
    step_run = StepRun(step_id="step_fail", run_id="run_123")
    step_run.mark_started()
    step_run.mark_failed("Connection timed out")
    assert step_run.status == StepStatus.FAILED
    assert step_run.error == "Connection timed out"


def test_step_run_skipped():
    step_run = StepRun(step_id="step_skip", run_id="run_123")
    step_run.mark_skipped("condition was false")
    assert step_run.status == StepStatus.SKIPPED
    assert "condition was false" in step_run.logs[0]


def test_workflow_run_lifecycle():
    run = WorkflowRun(run_id="run_abc", workflow_id="wf_abc")
    assert run.status == WorkflowStatus.PENDING

    run.mark_running()
    assert run.status == WorkflowStatus.RUNNING

    run.mark_success()
    assert run.status == WorkflowStatus.SUCCESS
    assert run.completed_at is not None
    assert run.duration_ms is not None


def test_workflow_run_failed():
    run = WorkflowRun(run_id="run_fail", workflow_id="wf_fail")
    run.mark_failed("Step X crashed")
    assert run.status == WorkflowStatus.FAILED
    assert run.error == "Step X crashed"
