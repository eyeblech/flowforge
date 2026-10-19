"""HTTP request action supporting async REST API interactions."""

import time
from typing import Any, Dict, List
import httpx
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("http")
class HttpAction(BaseAction):
    """Executes asynchronous HTTP requests."""

    name = "http"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        url = params.get("url")
        if not url:
            return ActionResult(success=False, error="Parameter 'url' is required for http action.")

        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        query_params = params.get("params", {})
        json_body = params.get("json")
        form_data = params.get("data")
        timeout = float(params.get("timeout", 30.0))
        allowed_statuses: List[int] = params.get("expected_status", [200, 201, 202, 204])
        if isinstance(allowed_statuses, int):
            allowed_statuses = [allowed_statuses]

        start_time = time.perf_counter()
        logs: List[str] = [f"Sending {method} request to {url}"]

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=query_params,
                    json=json_body,
                    data=form_data,
                )

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            logs.append(f"Received response status {response.status_code} in {elapsed_ms:.1f}ms")

            # Parse payload
            try:
                body_json = response.json()
            except Exception:
                body_json = None

            output_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "json": body_json,
                "text": response.text,
                "elapsed_ms": round(elapsed_ms, 2),
            }

            if allowed_statuses and response.status_code not in allowed_statuses:
                error_msg = (
                    f"HTTP request returned status {response.status_code}, "
                    f"expected one of {allowed_statuses}."
                )
                return ActionResult(
                    success=False,
                    output=output_data,
                    error=error_msg,
                    logs=logs,
                )

            return ActionResult(
                success=True,
                output=output_data,
                logs=logs,
            )

        except httpx.TimeoutException:
            logs.append(f"HTTP request timed out after {timeout}s")
            return ActionResult(
                success=False,
                error=f"HTTP request to {url} timed out after {timeout} seconds.",
                logs=logs,
            )
        except Exception as e:
            logs.append(f"HTTP request failed: {e}")
            return ActionResult(
                success=False,
                error=f"HTTP request error: {str(e)}",
                logs=logs,
            )
