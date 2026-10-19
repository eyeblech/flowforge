"""Tests for DAG validation, cycle detection, and topological ordering."""

import pytest
from flowforge.core.graph import WorkflowGraph, WorkflowGraphError
from flowforge.core.models import StepDefinition, WorkflowDefinition


def test_valid_dag_topological_sort():
    wf = WorkflowDefinition(
        id="valid_dag",
        name="Valid DAG",
        steps=[
            StepDefinition(id="c", action="shell", depends_on=["b"]),
            StepDefinition(id="a", action="shell"),
            StepDefinition(id="b", action="shell", depends_on=["a"]),
        ],
    )
    graph = WorkflowGraph(wf)
    order = graph.topological_order()
    assert order == ["a", "b", "c"]
    assert graph.get_root_steps() == ["a"]
    assert graph.get_prerequisites("b") == {"a"}
    assert graph.get_dependents("a") == {"b"}


def test_detect_direct_cycle():
    wf = WorkflowDefinition(
        id="cycle_wf",
        name="Cycle Workflow",
        steps=[
            StepDefinition(id="a", action="shell", depends_on=["b"]),
            StepDefinition(id="b", action="shell", depends_on=["a"]),
        ],
    )
    with pytest.raises(WorkflowGraphError, match="Cyclic dependency detected"):
        WorkflowGraph(wf)


def test_detect_self_dependency():
    wf = WorkflowDefinition(
        id="self_dep_wf",
        name="Self Dep Workflow",
        steps=[
            StepDefinition(id="a", action="shell", depends_on=["a"]),
        ],
    )
    with pytest.raises(WorkflowGraphError, match="cannot depend on itself"):
        WorkflowGraph(wf)


def test_detect_missing_dependency():
    wf = WorkflowDefinition(
        id="missing_dep_wf",
        name="Missing Dep Workflow",
        steps=[
            StepDefinition(id="step1", action="shell", depends_on=["non_existent_step"]),
        ],
    )
    with pytest.raises(WorkflowGraphError, match="does not exist in the workflow"):
        WorkflowGraph(wf)


def test_detect_duplicate_step_id():
    # Construct with duplicate steps
    s1 = StepDefinition(id="dup", action="shell")
    s2 = StepDefinition(id="dup", action="shell")
    # Pydantic validates list of StepDefinition, but WorkflowGraph checks unique step ids
    wf = WorkflowDefinition.model_construct(
        id="dup_wf",
        name="Dup Workflow",
        steps=[s1, s2],
    )
    with pytest.raises(WorkflowGraphError, match="Duplicate step ID"):
        WorkflowGraph(wf)
