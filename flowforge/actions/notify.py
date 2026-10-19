"""Notification dispatch action supporting Slack, Discord, and generic webhooks."""

from typing import Any, Dict, List
import httpx
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("notify")
class NotifyAction(BaseAction):
    """Sends notification alerts to Discord, Slack, or generic webhooks."""

    name = "notify"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        webhook_url = params.get("webhook_url") or params.get("url")
        if not webhook_url:
            return ActionResult(
                success=False, error="Parameter 'webhook_url' is required for notify action."
            )

        channel = params.get("channel", "generic").lower()
        message = str(params.get("message", ""))
        title = params.get("title", f"FlowForge Alert: {context.workflow_id}")
        level = params.get("level", "info").lower()

        color_map = {
            "info": 0x3498DB,      # Blue
            "success": 0x2ECC71,   # Green
            "warning": 0xF1C40F,   # Yellow
            "error": 0xE74C3C,     # Red
        }

        logs: List[str] = [f"Dispatching notification to {channel} webhook"]

        # Build payload based on platform
        payload: Dict[str, Any]
        if channel == "discord":
            payload = {
                "embeds": [
                    {
                        "title": title,
                        "description": message,
                        "color": color_map.get(level, 0x3498DB),
                        "footer": {"text": f"Workflow: {context.workflow_id} | Run: {context.run_id}"},
                    }
                ]
            }
        elif channel == "slack":
            emoji_map = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🚨"}
            payload = {
                "text": f"{emoji_map.get(level, 'ℹ️')} *{title}*\n{message}",
                "attachments": [
                    {
                        "color": f"#{color_map.get(level, 0x3498DB):06x}",
                        "text": f"Workflow `{context.workflow_id}` (Run: `{context.run_id}`)",
                    }
                ],
            }
        else:
            payload = {
                "title": title,
                "message": message,
                "level": level,
                "workflow_id": context.workflow_id,
                "run_id": context.run_id,
                "step_id": context.step_id,
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(webhook_url, json=payload)

            logs.append(f"Notification delivered with status {res.status_code}")
            if res.status_code >= 400:
                return ActionResult(
                    success=False,
                    error=f"Notification webhook failed with HTTP {res.status_code}: {res.text}",
                    logs=logs,
                )

            return ActionResult(
                success=True,
                output={"status_code": res.status_code, "channel": channel},
                logs=logs,
            )

        except Exception as e:
            logs.append(f"Notification dispatch error: {e}")
            return ActionResult(
                success=False,
                error=f"Notification error: {str(e)}",
                logs=logs,
            )
