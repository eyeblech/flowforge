"""LLM / AI decision and extraction action via OpenAI-compatible endpoints."""

import json
import os
from typing import Any, Dict, List
import httpx
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("llm")
class LlmAction(BaseAction):
    """Executes AI prompts and structured reasoning using OpenAI-compatible APIs."""

    name = "llm"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        prompt = params.get("prompt")
        if not prompt:
            return ActionResult(success=False, error="Parameter 'prompt' is required for llm action.")

        system_prompt = params.get("system", "You are an intelligent workflow automation assistant.")
        model = params.get("model", "gpt-4o-mini")
        temperature = float(params.get("temperature", 0.2))
        base_url = params.get("base_url") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        base_url = base_url.rstrip("/")
        api_key = (
            params.get("api_key")
            or os.environ.get("OPENAI_API_KEY")
            or context.context.get("env", {}).get("OPENAI_API_KEY", "")
        )
        json_mode = bool(params.get("json_mode", False))
        timeout = float(params.get("timeout", 60.0))

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}" if api_key else "",
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        endpoint = f"{base_url}/chat/completions"
        logs: List[str] = [f"Invoking LLM model '{model}' at {endpoint}"]

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(endpoint, json=payload, headers=headers)

            if res.status_code >= 400:
                return ActionResult(
                    success=False,
                    error=f"LLM API returned status {res.status_code}: {res.text}",
                    logs=logs,
                )

            data = res.json()
            raw_content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})

            output_json = None
            if json_mode:
                try:
                    output_json = json.loads(raw_content)
                except Exception:
                    pass

            logs.append(f"LLM completion succeeded ({usage.get('total_tokens', 0)} tokens)")

            return ActionResult(
                success=True,
                output={
                    "content": raw_content,
                    "json": output_json,
                    "model": model,
                    "usage": usage,
                },
                logs=logs,
            )

        except Exception as e:
            logs.append(f"LLM invocation failed: {e}")
            return ActionResult(
                success=False,
                error=f"LLM action error: {str(e)}",
                logs=logs,
            )
