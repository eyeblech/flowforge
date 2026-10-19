"""Abstract BaseStorage interface for workflow and run persistence."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from flowforge.core.models import StepRun, WorkflowDefinition, WorkflowRun


class BaseStorage(ABC):
    """Abstract interface defining required storage operations."""

    @abstractmethod
    def save_workflow(self, workflow: WorkflowDefinition) -> None:
        """Persist or update a workflow definition."""
        pass

    @abstractmethod
    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieve a workflow definition by its unique ID."""
        pass

    @abstractmethod
    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all stored workflow definitions."""
        pass

    @abstractmethod
    def create_run(self, run: WorkflowRun) -> None:
        """Create a new workflow execution run record."""
        pass

    @abstractmethod
    def update_run(self, run: WorkflowRun) -> None:
        """Update an existing workflow execution run record."""
        pass

    @abstractmethod
    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Retrieve a workflow execution run by ID including its step runs."""
        pass

    @abstractmethod
    def list_runs(
        self, workflow_id: Optional[str] = None, limit: int = 50
    ) -> List[WorkflowRun]:
        """List recent workflow runs, optionally filtered by workflow ID."""
        pass

    @abstractmethod
    def save_step_run(self, step_run: StepRun) -> None:
        """Persist or update execution state for an individual step."""
        pass

    @abstractmethod
    def get_step_runs(self, run_id: str) -> Dict[str, StepRun]:
        """Retrieve all step runs associated with a given workflow run ID."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close storage connections and flush resources."""
        pass
