"""Cron scheduler for timed periodic workflow execution."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from croniter import croniter
from flowforge.core.models import TriggerType, WorkflowDefinition
from flowforge.engine.runner import WorkflowEngine
from flowforge.triggers.base import BaseTrigger
from flowforge.utils.logger import logger


class ScheduledJob:
    """Represents a scheduled workflow cron job."""

    def __init__(self, workflow: WorkflowDefinition, expression: str) -> None:
        self.workflow = workflow
        self.expression = expression
        self.iter = croniter(expression, datetime.now(timezone.utc))
        self.next_run: datetime = self.iter.get_next(datetime)

    def advance(self) -> None:
        """Calculate next scheduled run time."""
        self.next_run = self.iter.get_next(datetime)


class CronScheduler(BaseTrigger):
    """Background cron scheduler running registered workflows."""

    def __init__(self, engine: WorkflowEngine) -> None:
        self.engine = engine
        self.jobs: Dict[str, ScheduledJob] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register workflow if it has a CRON trigger."""
        for trigger in workflow.triggers:
            if trigger.type == TriggerType.CRON:
                expr = trigger.config.get("expression")
                if expr and croniter.is_valid(expr):
                    self.jobs[workflow.id] = ScheduledJob(workflow, expr)
                    logger.info(
                        "Registered cron job for '%s': '%s' (Next: %s)",
                        workflow.id,
                        expr,
                        self.jobs[workflow.id].next_run.isoformat(),
                    )

    def unregister_workflow(self, workflow_id: str) -> None:
        """Unregister workflow from scheduler."""
        self.jobs.pop(workflow_id, None)

    async def start(self) -> None:
        """Start the cron scheduler loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="cron_scheduler")

    async def stop(self) -> None:
        """Stop the cron scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        """Continuous polling scheduler loop."""
        while self._running:
            now = datetime.now(timezone.utc)
            for job in list(self.jobs.values()):
                if now >= job.next_run:
                    job.advance()
                    logger.info("Firing scheduled run for workflow '%s'", job.workflow.id)
                    # Launch asynchronously in background
                    asyncio.create_task(
                        self.engine.execute(
                            workflow=job.workflow,
                            trigger_type="cron",
                            trigger_payload={"scheduled_at": now.isoformat()},
                        )
                    )

            await asyncio.sleep(1.0)
