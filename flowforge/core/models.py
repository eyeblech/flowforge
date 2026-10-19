"""Core data models and schemas for FlowForge workflows and executions."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class StepStatus(str, Enum):
    """Execution status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    """Overall status of a workflow execution run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIALLY_FAILED = "partially_failed"


class TriggerType(str, Enum):
    """Supported trigger types."""
    MANUAL = "manual"
    CRON = "cron"
    WEBHOOK = "webhook"
    FILE_WATCH = "file_watch"


class RetryPolicy(BaseModel):
    """Configuration for automatic step retries with exponential backoff."""
    max_attempts: int = Field(default=3, ge=1, description="Maximum total attempts (1 = no retry)")
    initial_delay: float = Field(default=1.0, ge=0.0, description="Initial delay in seconds")
    backoff_multiplier: float = Field(default=2.0, ge=1.0, description="Multiplier for backoff")
    max_delay: float = Field(default=60.0, ge=0.0, description="Cap on maximum retry delay")
    jitter: bool = Field(default=True, description="Add randomized jitter to avoid thundering herd")

    model_config = ConfigDict(extra="ignore")


class TriggerDefinition(BaseModel):
    """Definition of a trigger event that can start workflow execution."""
    type: TriggerType = Field(..., description="Type of trigger (cron, webhook, file_watch, manual)")
    config: Dict[str, Any] = Field(default_factory=dict, description="Trigger-specific configuration")

    model_config = ConfigDict(extra="ignore")


class StepDefinition(BaseModel):
    """Definition of a single step within a workflow DAG."""
    id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique identifier for the step")
    name: Optional[str] = Field(default=None, description="Human readable label for the step")
    action: str = Field(..., description="Action handler identifier (e.g., 'http', 'shell', 'transform')")
    with_params: Dict[str, Any] = Field(default_factory=dict, alias="with", description="Parameters passed to action")
    depends_on: List[str] = Field(default_factory=list, description="List of step IDs that must complete first")
    when: Optional[str] = Field(default=None, description="Condition template expression; executes if truthy")
    retry: Optional[RetryPolicy] = Field(default=None, description="Step-level retry policy")
    timeout: Optional[float] = Field(default=None, gt=0, description="Execution timeout in seconds")
    continue_on_error: bool = Field(default=False, description="If True, downstream steps continue on failure")
    description: Optional[str] = Field(default=None, description="Optional step documentation")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class WorkflowDefinition(BaseModel):
    """Complete specification of a FlowForge workflow."""
    id: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Unique workflow identifier")
    name: str = Field(..., description="Descriptive workflow name")
    version: str = Field(default="1.0", description="Semantic workflow version")
    description: Optional[str] = Field(default=None, description="Workflow documentation and goals")
    env: Dict[str, str] = Field(default_factory=dict, description="Default environment variables")
    triggers: List[TriggerDefinition] = Field(default_factory=list, description="Triggers that invoke this workflow")
    concurrency: int = Field(default=10, ge=1, le=100, description="Maximum parallel steps allowed")
    timeout: Optional[float] = Field(default=None, gt=0, description="Global workflow execution timeout in seconds")
    steps: List[StepDefinition] = Field(..., min_length=1, description="List of step definitions forming the DAG")

    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class StepRun(BaseModel):
    """Runtime execution snapshot and history of a specific step."""
    step_id: str
    run_id: str
    status: StepStatus = StepStatus.PENDING
    attempt: int = 1
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_data: Any = None
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    def mark_started(self) -> None:
        """Mark step as running."""
        self.status = StepStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)

    def mark_success(self, output: Any = None) -> None:
        """Mark step as successfully completed."""
        self.status = StepStatus.SUCCESS
        self.completed_at = datetime.now(timezone.utc)
        self.output_data = output
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0

    def mark_failed(self, error: str) -> None:
        """Mark step as failed."""
        self.status = StepStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0

    def mark_skipped(self, reason: Optional[str] = None) -> None:
        """Mark step as skipped due to condition or upstream failure."""
        self.status = StepStatus.SKIPPED
        self.completed_at = datetime.now(timezone.utc)
        if reason:
            self.logs.append(f"Skipped: {reason}")


class WorkflowRun(BaseModel):
    """Runtime execution snapshot and context of a complete workflow."""
    run_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    trigger_type: str = "manual"
    trigger_payload: Dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    step_runs: Dict[str, StepRun] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None

    model_config = ConfigDict(extra="ignore")

    def mark_running(self) -> None:
        """Mark workflow as active."""
        self.status = WorkflowStatus.RUNNING

    def mark_success(self) -> None:
        """Mark workflow as successful."""
        self.status = WorkflowStatus.SUCCESS
        self.completed_at = datetime.now(timezone.utc)
        self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0

    def mark_failed(self, error: str) -> None:
        """Mark workflow as failed."""
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.error = error
        if self.started_at:
            self.duration_ms = (self.completed_at - self.started_at).total_seconds() * 1000.0
