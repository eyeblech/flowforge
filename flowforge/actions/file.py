"""File system interaction action."""

import json
from pathlib import Path
from typing import Any, Dict, List
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("file")
class FileAction(BaseAction):
    """Performs file system operations like read, write, append, and exists."""

    name = "file"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        operation = params.get("operation", "read").lower()
        path_str = params.get("path")
        if not path_str:
            return ActionResult(success=False, error="Parameter 'path' is required for file action.")

        target_path = Path(path_str)
        encoding = params.get("encoding", "utf-8")
        logs: List[str] = [f"Performing '{operation}' on path: {target_path}"]

        try:
            if operation == "read":
                if not target_path.exists():
                    return ActionResult(
                        success=False,
                        error=f"File does not exist: {target_path}",
                        logs=logs,
                    )
                content = target_path.read_text(encoding=encoding)
                # Try parsing JSON if content appears to be JSON
                is_json = False
                parsed_json = None
                try:
                    parsed_json = json.loads(content)
                    is_json = True
                except Exception:
                    pass

                output = {
                    "content": content,
                    "size_bytes": target_path.stat().st_size,
                    "is_json": is_json,
                    "json": parsed_json,
                }
                return ActionResult(success=True, output=output, logs=logs)

            elif operation == "write":
                content = params.get("content", "")
                if not isinstance(content, str):
                    content = json.dumps(content, indent=2, default=str)

                if params.get("make_parents", True):
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                target_path.write_text(content, encoding=encoding)
                logs.append(f"Wrote {len(content)} characters to {target_path}")
                return ActionResult(
                    success=True,
                    output={"path": str(target_path.resolve()), "bytes_written": len(content.encode(encoding))},
                    logs=logs,
                )

            elif operation == "append":
                content = params.get("content", "")
                if not isinstance(content, str):
                    content = json.dumps(content, default=str)

                if params.get("make_parents", True):
                    target_path.parent.mkdir(parents=True, exist_ok=True)

                with open(target_path, "a", encoding=encoding) as f:
                    f.write(content)

                logs.append(f"Appended {len(content)} characters to {target_path}")
                return ActionResult(
                    success=True,
                    output={"path": str(target_path.resolve()), "bytes_appended": len(content.encode(encoding))},
                    logs=logs,
                )

            elif operation == "exists":
                exists = target_path.exists()
                is_dir = target_path.is_dir() if exists else False
                is_file = target_path.is_file() if exists else False
                return ActionResult(
                    success=True,
                    output={"exists": exists, "is_file": is_file, "is_dir": is_dir},
                    logs=logs,
                )

            elif operation == "delete":
                if target_path.exists():
                    if target_path.is_file():
                        target_path.unlink()
                    elif target_path.is_dir():
                        target_path.rmdir()
                    logs.append(f"Deleted {target_path}")
                return ActionResult(success=True, output={"deleted": True}, logs=logs)

            elif operation == "list":
                if not target_path.exists() or not target_path.is_dir():
                    return ActionResult(
                        success=False,
                        error=f"Directory does not exist: {target_path}",
                        logs=logs,
                    )
                entries = [p.name for p in target_path.iterdir()]
                return ActionResult(success=True, output={"files": entries}, logs=logs)

            else:
                return ActionResult(
                    success=False,
                    error=f"Unknown file operation: '{operation}'. Supported: read, write, append, exists, delete, list",
                    logs=logs,
                )

        except Exception as e:
            logs.append(f"File operation failed: {e}")
            return ActionResult(
                success=False,
                error=f"File operation error: {str(e)}",
                logs=logs,
            )
