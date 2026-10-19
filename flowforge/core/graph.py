"""Directed Acyclic Graph (DAG) analysis, cycle detection, and dependency resolution."""

from collections import defaultdict, deque
from typing import Dict, List, Set
from flowforge.core.models import StepDefinition, WorkflowDefinition


class WorkflowGraphError(Exception):
    """Raised when workflow DAG validation fails (cycle, missing node, etc.)."""
    pass


class WorkflowGraph:
    """Represents the Directed Acyclic Graph of workflow steps."""

    def __init__(self, workflow: WorkflowDefinition) -> None:
        self.workflow = workflow
        self.step_map: Dict[str, StepDefinition] = {step.id: step for step in workflow.steps}
        self.adjacency: Dict[str, Set[str]] = defaultdict(set)  # step_id -> dependent step_ids
        self.in_degree: Dict[str, int] = {step.id: 0 for step in workflow.steps}
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)  # step_id -> prerequisites

        self._build_graph()

    def _build_graph(self) -> None:
        """Construct graph and validate node references."""
        # 1. Validate uniqueness
        if len(self.step_map) != len(self.workflow.steps):
            seen = set()
            duplicates = []
            for step in self.workflow.steps:
                if step.id in seen:
                    duplicates.append(step.id)
                seen.add(step.id)
            raise WorkflowGraphError(f"Duplicate step ID(s) found in workflow: {duplicates}")

        # 2. Build edges & validate dependencies
        for step in self.workflow.steps:
            for dep in step.depends_on:
                if dep not in self.step_map:
                    raise WorkflowGraphError(
                        f"Step '{step.id}' depends on '{dep}', which does not exist in the workflow."
                    )
                if dep == step.id:
                    raise WorkflowGraphError(f"Step '{step.id}' cannot depend on itself.")

                self.adjacency[dep].add(step.id)
                self.dependencies[step.id].add(dep)
                self.in_degree[step.id] += 1

        # 3. Detect cycles
        self._check_cycles()

    def _check_cycles(self) -> None:
        """Detect cycles using Kahn's algorithm."""
        in_deg = dict(self.in_degree)
        queue = deque([node for node, deg in in_deg.items() if deg == 0])
        visited_count = 0

        while queue:
            node = queue.popleft()
            visited_count += 1
            for neighbor in self.adjacency[node]:
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        if visited_count != len(self.step_map):
            cycle_nodes = [node for node, deg in in_deg.items() if deg > 0]
            raise WorkflowGraphError(
                f"Cyclic dependency detected among steps: {cycle_nodes}"
            )

    def get_root_steps(self) -> List[str]:
        """Return steps that have no dependencies and can start immediately."""
        return [step.id for step in self.workflow.steps if not step.depends_on]

    def get_dependents(self, step_id: str) -> Set[str]:
        """Return steps that directly depend on the given step."""
        return self.adjacency.get(step_id, set())

    def get_prerequisites(self, step_id: str) -> Set[str]:
        """Return steps that the given step directly depends on."""
        return self.dependencies.get(step_id, set())

    def topological_order(self) -> List[str]:
        """Return a valid linear execution order of step IDs."""
        in_deg = dict(self.in_degree)
        queue = deque([node for node, deg in in_deg.items() if deg == 0])
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in sorted(self.adjacency[node]):
                in_deg[neighbor] -= 1
                if in_deg[neighbor] == 0:
                    queue.append(neighbor)

        return order

    def is_step_ready(self, step_id: str, completed_step_ids: Set[str]) -> bool:
        """Check if all prerequisite dependencies of a step have finished."""
        prereqs = self.dependencies.get(step_id, set())
        return prereqs.issubset(completed_step_ids)
