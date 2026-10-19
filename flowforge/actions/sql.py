"""SQL query execution action for SQLite databases."""

import sqlite3
from typing import Any, Dict, List
from flowforge.actions.base import ActionContext, ActionResult, BaseAction, register_action


@register_action("sql")
class SqlAction(BaseAction):
    """Executes SQL statements and queries against a SQLite database."""

    name = "sql"

    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        query = params.get("query")
        if not query:
            return ActionResult(success=False, error="Parameter 'query' is required for sql action.")

        db_path = params.get("database", "flowforge.db")
        sql_params = params.get("params", [])
        fetch = params.get("fetch", True)

        logs: List[str] = [f"Executing SQL query on {db_path}: {query[:100]}..."]

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if isinstance(sql_params, dict):
                cursor.execute(query, sql_params)
            elif isinstance(sql_params, list):
                cursor.execute(query, tuple(sql_params))
            else:
                cursor.execute(query)

            rows_affected = cursor.rowcount
            data: List[Dict[str, Any]] = []

            # If it's a SELECT or returns rows
            if fetch and cursor.description:
                rows = cursor.fetchall()
                data = [dict(row) for row in rows]
                logs.append(f"Query returned {len(data)} rows")
            else:
                conn.commit()
                logs.append(f"Query executed successfully, {rows_affected} rows affected")

            conn.close()

            return ActionResult(
                success=True,
                output={
                    "rows": data,
                    "row_count": len(data) if data else rows_affected,
                    "rows_affected": rows_affected,
                },
                logs=logs,
            )

        except Exception as e:
            logs.append(f"SQL execution error: {e}")
            return ActionResult(
                success=False,
                error=f"SQL error: {str(e)}",
                logs=logs,
            )
