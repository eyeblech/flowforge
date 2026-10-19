"""Shell command execution action."""

import asyncio
import os
import time
from typing import Any, Dict, List, Optional
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("shell")
class ShellAction(BaseAction):
    """Executes asynchronous shell commands and scripts."""

    name = "shell"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        command = params.get("command") or params.get("script")
        if not command:
            return ActionResult(success=False, error="Parameter 'command' or 'script' is required for shell action.")

        cwd = params.get("cwd")
        timeout: Optional[float] = params.get("timeout")
        fail_on_error = params.get("fail_on_error", True)
        extra_env = params.get("env", {})

        env = os.environ.copy()
        if extra_env and isinstance(extra_env, dict):
            for k, v in extra_env.items():
                env[str(k)] = str(v)

        logs: List[str] = [f"Executing shell command: {command}"]
        start_time = time.perf_counter()

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env,
            )

            if timeout:
                try:
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(
                        process.communicate(), timeout=float(timeout)
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    await process.wait()
                    logs.append(f"Command timed out after {timeout}s and was terminated.")
                    return ActionResult(
                        success=False,
                        error=f"Command timed out after {timeout} seconds.",
                        logs=logs,
                    )
            else:
                stdout_bytes, stderr_bytes = await process.communicate()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            stdout_str = stdout_bytes.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_bytes.decode("utf-8", errors="replace").strip()
            exit_code = process.returncode or 0

            logs.append(f"Command exited with code {exit_code} in {elapsed_ms:.1f}ms")

            output_data = {
                "exit_code": exit_code,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "elapsed_ms": round(elapsed_ms, 2),
            }

            if exit_code != 0 and fail_on_error:
                return ActionResult(
                    success=False,
                    output=output_data,
                    error=f"Command exited with non-zero code {exit_code}: {stderr_str or stdout_str}",
                    logs=logs,
                )

            return ActionResult(
                success=True,
                output=output_data,
                logs=logs,
            )

        except Exception as e:
            logs.append(f"Command execution error: {e}")
            return ActionResult(
                success=False,
                error=f"Shell execution failed: {str(e)}",
                logs=logs,
            )
