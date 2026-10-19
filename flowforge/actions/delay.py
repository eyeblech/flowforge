"""Delay/sleep action for timed waits between workflow steps."""

import asyncio
from typing import Any, Dict, List
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("delay")
class DelayAction(BaseAction):
    """Pauses execution for a specified duration."""

    name = "delay"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        seconds = float(params.get("seconds", 1.0))
        logs: List[str] = [f"Pausing execution for {seconds} seconds"]

        await asyncio.sleep(seconds)
        logs.append("Delay finished")

        return ActionResult(
            success=True,
            output={"slept_seconds": seconds},
            logs=logs,
        )
