"""Event system and telemetry bus for workflow and step lifecycles."""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Lifecycle event types emitted during execution."""
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    STEP_SKIPPED = "step.skipped"
    STEP_RETRYING = "step.retrying"


class EngineEvent(BaseModel):
    """Event payload emitted by the workflow engine."""
    event_type: EventType
    workflow_id: str
    run_id: str
    step_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


EventHandler = Callable[[EngineEvent], Union[None, Coroutine[Any, Any, None]]]


class EventBus:
    """Asynchronous event dispatcher for telemetry and live progress reporting."""

    def __init__(self) -> None:
        self._handlers: List[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        """Register a callback handler for engine events."""
        if handler not in self._handlers:
            self._handlers.append(handler)

    def unsubscribe(self, handler: EventHandler) -> None:
        """Unregister a callback handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)

    async def emit(self, event: EngineEvent) -> None:
        """Publish an event to all subscribed listeners."""
        for handler in self._handlers:
            try:
                res = handler(event)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                pass  # Event emission must not break the engine
