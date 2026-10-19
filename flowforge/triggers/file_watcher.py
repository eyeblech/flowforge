"""File watcher trigger for filesystem event-based workflow execution."""

import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from flowforge.core.models import TriggerType, WorkflowDefinition
from flowforge.engine.runner import WorkflowEngine
from flowforge.triggers.base import BaseTrigger
from flowforge.utils.logger import logger


class FileWatcherTrigger(BaseTrigger):
    """Watches specified directory paths and triggers workflows when files appear or change."""

    def __init__(self, engine: WorkflowEngine) -> None:
        self.engine = engine
        self.watches: List[Dict[str, Any]] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._known_mtimes: Dict[str, float] = {}

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """Register workflow if it specifies a FILE_WATCH trigger."""
        for trigger in workflow.triggers:
            if trigger.type == TriggerType.FILE_WATCH:
                watch_path = trigger.config.get("path")
                pattern = trigger.config.get("pattern", "*")
                if watch_path:
                    p = Path(watch_path)
                    p.mkdir(parents=True, exist_ok=True)
                    self.watches.append(
                        {
                            "workflow": workflow,
                            "path": p,
                            "pattern": pattern,
                        }
                    )
                    logger.info("Registered file watcher for '%s' on %s (%s)", workflow.id, p, pattern)

    async def start(self) -> None:
        """Start polling watched directories."""
        if self._running or not self.watches:
            return
        self._running = True

        # Initialize current state so we don't trigger on existing files at startup
        for item in self.watches:
            p: Path = item["path"]
            pattern: str = item["pattern"]
            for file_path in p.glob(pattern):
                if file_path.is_file():
                    try:
                        self._known_mtimes[str(file_path)] = file_path.stat().st_mtime
                    except Exception:
                        pass

        self._task = asyncio.create_task(self._poll_loop(), name="file_watcher")

    async def stop(self) -> None:
        """Stop file watcher loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) -> None:
        while self._running:
            for item in self.watches:
                p: Path = item["path"]
                pattern: str = item["pattern"]
                workflow: WorkflowDefinition = item["workflow"]

                try:
                    for file_path in p.glob(pattern):
                        if not file_path.is_file():
                            continue
                        f_str = str(file_path)
                        try:
                            mtime = file_path.stat().st_mtime
                        except Exception:
                            continue

                        if f_str not in self._known_mtimes or mtime > self._known_mtimes[f_str]:
                            event_type = "created" if f_str not in self._known_mtimes else "modified"
                            self._known_mtimes[f_str] = mtime

                            logger.info(
                                "File watcher event '%s' on %s triggering '%s'",
                                event_type,
                                file_path.name,
                                workflow.id,
                            )
                            asyncio.create_task(
                                self.engine.execute(
                                    workflow=workflow,
                                    trigger_type="file_watch",
                                    trigger_payload={
                                        "event": event_type,
                                        "path": f_str,
                                        "filename": file_path.name,
                                        "size_bytes": file_path.stat().st_size,
                                    },
                                )
                            )
                except Exception as e:
                    logger.warning("Error checking watch path %s: %s", p, e)

            await asyncio.sleep(2.0)
