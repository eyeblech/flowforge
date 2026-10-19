"""Pytest fixtures and test configurations for FlowForge."""

import pytest
from pathlib import Path
from flowforge.core.models import (
    RetryPolicy,
    StepDefinition,
    WorkflowDefinition,
)
from flowforge.storage.memory import MemoryStorage
from flowforge.engine.runner import WorkflowEngine


@pytest.fixture
def memory_storage() -> MemoryStorage:
    """Provide clean in-memory storage backend."""
    return MemoryStorage()


@pytest.fixture
def workflow_engine(memory_storage: MemoryStorage) -> WorkflowEngine:
    """Provide workflow engine with in-memory storage."""
    return WorkflowEngine(storage=memory_storage)


@pytest.fixture
def sample_linear_workflow() -> WorkflowDefinition:
    """Provide a simple 2-step linear workflow."""
    return WorkflowDefinition(
        id="test_linear_wf",
        name="Test Linear Workflow",
        steps=[
            StepDefinition(
                id="step_one",
                action="transform",
                **{"with": {"value": {"msg": "hello from step one"}}},
            ),
            StepDefinition(
                id="step_two",
                action="transform",
                depends_on=["step_one"],
                **{"with": {"value": {"echo": "{{ steps.step_one.output.msg }}"}}},
            ),
        ],
    )


@pytest.fixture
def sample_branching_workflow() -> WorkflowDefinition:
    """Provide a branching workflow with parallel nodes."""
    return WorkflowDefinition(
        id="test_branching_wf",
        name="Test Branching Workflow",
        steps=[
            StepDefinition(
                id="root",
                action="transform",
                **{"with": {"value": {"count": 10}}},
            ),
            StepDefinition(
                id="branch_a",
                action="transform",
                depends_on=["root"],
                **{"with": {"value": {"a": 1}}},
            ),
            StepDefinition(
                id="branch_b",
                action="transform",
                depends_on=["root"],
                **{"with": {"value": {"b": 2}}},
            ),
            StepDefinition(
                id="join",
                action="transform",
                depends_on=["branch_a", "branch_b"],
                **{"with": {"value": {"sum": 3}}},
            ),
        ],
    )
