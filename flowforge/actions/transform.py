"""Data transformation and projection action."""

from typing import Any, Dict, List
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("transform")
class TransformAction(BaseAction):
    """Transforms, projects, filters, or formats data structures."""

    name = "transform"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        logs: List[str] = ["Performing data transformation"]

        # 1. Direct value evaluation
        if "value" in params:
            val = params["value"]
            return ActionResult(success=True, output=val, logs=logs)

        # 2. Key mapping
        if "mapping" in params and isinstance(params["mapping"], dict):
            mapping = params["mapping"]
            logs.append(f"Mapped {len(mapping)} fields")
            return ActionResult(success=True, output=mapping, logs=logs)

        # 3. List projection or filtering
        items = params.get("items")
        if items is not None and isinstance(items, list):
            limit = params.get("limit")
            result_items = items
            if limit is not None and isinstance(limit, int):
                result_items = result_items[:limit]
            return ActionResult(success=True, output=result_items, logs=logs)

        # Default fallback: return all params
        return ActionResult(success=True, output=params, logs=logs)
