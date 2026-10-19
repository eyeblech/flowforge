"""In-memory storage backend for testing and ephemeral executions."""

from typing import Dict, List, Optional
from flowforge.core.models import StepRun, WorkflowDefinition, WorkflowRun
from flowforge.storage.base import BaseStorage


class MemoryStorage(BaseStorage):
    """Thread-safe in-memory store."""

    def __init__(self) -> None:
        self.workflows: Dict[str, WorkflowDefinition] = {}
        self.runs: Dict[str, WorkflowRun] = {}
        self.step_runs: Dict[str, Dict[str, StepRun]] = {}

    def save_workflow(self, workflow: WorkflowDefinition) -> None:
        self.workflows[workflow.id] = workflow.model_copy(deep=True)

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        wf = self.workflows.get(workflow_id)
        return wf.model_copy(deep=True) if wf else None

    def list_workflows(self) -> List[WorkflowDefinition]:
        return [wf.model_copy(deep=True) for wf in self.workflows.values()]

    def create_run(self, run: WorkflowRun) -> None:
        self.runs[run.run_id] = run.model_copy(deep=True)
        if run.run_id not in self.step_runs:
            self.step_runs[run.run_id] = {}

    def update_run(self, run: WorkflowRun) -> None:
        if run.run_id in self.runs:
            self.runs[run.run_id] = run.model_copy(deep=True)

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        run = self.runs.get(run_id)
        if not run:
            return None
        copied = run.model_copy(deep=True)
        copied.step_runs = {k: v.model_copy(deep=True) for k, v in self.step_runs.get(run_id, {}).items()}
        return copied

    def list_runs(
        self, workflow_id: Optional[str] = None, limit: int = 50
    ) -> List[WorkflowRun]:
        filtered = [
            r for r in self.runs.values()
            if workflow_id is None or r.workflow_id == workflow_id
        ]
        sorted_runs = sorted(filtered, key=lambda x: x.started_at, reverse=True)[:limit]
        result = []
        for r in sorted_runs:
            copied = r.model_copy(deep=True)
            copied.step_runs = {k: v.model_copy(deep=True) for k, v in self.step_runs.get(r.run_id, {}).items()}
            result.append(copied)
        return result

    def save_step_run(self, step_run: StepRun) -> None:
        if step_run.run_id not in self.step_runs:
            self.step_runs[step_run.run_id] = {}
        self.step_runs[step_run.run_id][step_run.step_id] = step_run.model_copy(deep=True)
        # Also update parent run if cached
        if step_run.run_id in self.runs:
            self.runs[step_run.run_id].step_runs[step_run.step_id] = step_run.model_copy(deep=True)

    def get_step_runs(self, run_id: str) -> Dict[str, StepRun]:
        return {k: v.model_copy(deep=True) for k, v in self.step_runs.get(run_id, {}).items()}

    def close(self) -> None:
        pass
