"""SQLite storage implementation with WAL mode and transaction safety."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from flowforge.core.models import (
    StepRun,
    StepStatus,
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStatus,
)
from flowforge.storage.base import BaseStorage


def _json_serialize(obj: Any) -> str:
    """Safely serialize objects to JSON string."""
    def _default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if hasattr(o, "model_dump"):
            return o.model_dump()
        return str(o)
    return json.dumps(obj, default=_default)


def _parse_dt(val: Optional[str]) -> Optional[datetime]:
    """Parse ISO formatted timestamp string."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val)
    except Exception:
        return None


class SQLiteStorage(BaseStorage):
    """High-performance SQLite storage backend for workflows and execution telemetry."""

    def __init__(self, db_path: Union[str, Path] = "flowforge.db") -> None:
        self.db_path = str(db_path)
        # Ensure parent directory exists
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema and set WAL pragma."""
        with self._conn:
            if self.db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL;")
            self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    version TEXT NOT NULL,
                    definition_json TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
            """)

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS workflow_runs (
                    run_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_payload_json TEXT NOT NULL,
                    started_at TIMESTAMP NOT NULL,
                    completed_at TIMESTAMP,
                    duration_ms REAL,
                    context_json TEXT NOT NULL,
                    error TEXT
                );
            """)

            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS step_runs (
                    step_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempt INTEGER NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    duration_ms REAL,
                    input_data_json TEXT NOT NULL,
                    output_data_json TEXT,
                    error TEXT,
                    logs_json TEXT NOT NULL,
                    PRIMARY KEY (step_id, run_id)
                );
            """)

            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_workflow_runs_wf_started 
                ON workflow_runs (workflow_id, started_at DESC);
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_step_runs_run_id 
                ON step_runs (run_id);
            """)

    def save_workflow(self, workflow: WorkflowDefinition) -> None:
        """Persist or update a workflow definition."""
        now_iso = datetime.now(timezone.utc).isoformat()
        raw_json = _json_serialize(workflow.model_dump())
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO workflows (id, name, version, definition_json, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name,
                    version=excluded.version,
                    definition_json=excluded.definition_json,
                    updated_at=excluded.updated_at
                """,
                (workflow.id, workflow.name, workflow.version, raw_json, now_iso),
            )

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieve a workflow definition by its unique ID."""
        cursor = self._conn.execute(
            "SELECT definition_json FROM workflows WHERE id = ?", (workflow_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return WorkflowDefinition.model_validate(json.loads(row["definition_json"]))

    def list_workflows(self) -> List[WorkflowDefinition]:
        """List all stored workflow definitions."""
        cursor = self._conn.execute("SELECT definition_json FROM workflows ORDER BY id ASC")
        return [
            WorkflowDefinition.model_validate(json.loads(row["definition_json"]))
            for row in cursor.fetchall()
        ]

    def create_run(self, run: WorkflowRun) -> None:
        """Create a new workflow execution run record."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO workflow_runs (
                    run_id, workflow_id, status, trigger_type, trigger_payload_json,
                    started_at, completed_at, duration_ms, context_json, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    run.workflow_id,
                    run.status.value,
                    run.trigger_type,
                    _json_serialize(run.trigger_payload),
                    run.started_at.isoformat(),
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.duration_ms,
                    _json_serialize(run.context),
                    run.error,
                ),
            )

    def update_run(self, run: WorkflowRun) -> None:
        """Update an existing workflow execution run record."""
        with self._conn:
            self._conn.execute(
                """
                UPDATE workflow_runs SET
                    status = ?,
                    completed_at = ?,
                    duration_ms = ?,
                    context_json = ?,
                    error = ?
                WHERE run_id = ?
                """,
                (
                    run.status.value,
                    run.completed_at.isoformat() if run.completed_at else None,
                    run.duration_ms,
                    _json_serialize(run.context),
                    run.error,
                    run.run_id,
                ),
            )

    def save_step_run(self, step_run: StepRun) -> None:
        """Persist or update execution state for an individual step."""
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO step_runs (
                    step_id, run_id, status, attempt, started_at, completed_at,
                    duration_ms, input_data_json, output_data_json, error, logs_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(step_id, run_id) DO UPDATE SET
                    status=excluded.status,
                    attempt=excluded.attempt,
                    started_at=excluded.started_at,
                    completed_at=excluded.completed_at,
                    duration_ms=excluded.duration_ms,
                    input_data_json=excluded.input_data_json,
                    output_data_json=excluded.output_data_json,
                    error=excluded.error,
                    logs_json=excluded.logs_json
                """,
                (
                    step_run.step_id,
                    step_run.run_id,
                    step_run.status.value,
                    step_run.attempt,
                    step_run.started_at.isoformat() if step_run.started_at else None,
                    step_run.completed_at.isoformat() if step_run.completed_at else None,
                    step_run.duration_ms,
                    _json_serialize(step_run.input_data),
                    _json_serialize(step_run.output_data) if step_run.output_data is not None else None,
                    step_run.error,
                    _json_serialize(step_run.logs),
                ),
            )

    def get_step_runs(self, run_id: str) -> Dict[str, StepRun]:
        """Retrieve all step runs associated with a given workflow run ID."""
        cursor = self._conn.execute(
            "SELECT * FROM step_runs WHERE run_id = ? ORDER BY started_at ASC", (run_id,)
        )
        step_runs: Dict[str, StepRun] = {}
        for row in cursor.fetchall():
            step_runs[row["step_id"]] = StepRun(
                step_id=row["step_id"],
                run_id=row["run_id"],
                status=StepStatus(row["status"]),
                attempt=row["attempt"],
                started_at=_parse_dt(row["started_at"]),
                completed_at=_parse_dt(row["completed_at"]),
                duration_ms=row["duration_ms"],
                input_data=json.loads(row["input_data_json"]),
                output_data=json.loads(row["output_data_json"]) if row["output_data_json"] else None,
                error=row["error"],
                logs=json.loads(row["logs_json"]),
            )
        return step_runs

    def get_run(self, run_id: str) -> Optional[WorkflowRun]:
        """Retrieve a workflow execution run by ID including its step runs."""
        cursor = self._conn.execute(
            "SELECT * FROM workflow_runs WHERE run_id = ?", (run_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None

        step_runs = self.get_step_runs(run_id)
        return WorkflowRun(
            run_id=row["run_id"],
            workflow_id=row["workflow_id"],
            status=WorkflowStatus(row["status"]),
            trigger_type=row["trigger_type"],
            trigger_payload=json.loads(row["trigger_payload_json"]),
            started_at=_parse_dt(row["started_at"]) or datetime.now(timezone.utc),
            completed_at=_parse_dt(row["completed_at"]),
            duration_ms=row["duration_ms"],
            step_runs=step_runs,
            context=json.loads(row["context_json"]),
            error=row["error"],
        )

    def list_runs(
        self, workflow_id: Optional[str] = None, limit: int = 50
    ) -> List[WorkflowRun]:
        """List recent workflow runs, optionally filtered by workflow ID."""
        if workflow_id:
            cursor = self._conn.execute(
                """
                SELECT * FROM workflow_runs 
                WHERE workflow_id = ? 
                ORDER BY started_at DESC LIMIT ?
                """,
                (workflow_id, limit),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT * FROM workflow_runs 
                ORDER BY started_at DESC LIMIT ?
                """,
                (limit,),
            )

        runs: List[WorkflowRun] = []
        for row in cursor.fetchall():
            run_id = row["run_id"]
            step_runs = self.get_step_runs(run_id)
            runs.append(
                WorkflowRun(
                    run_id=run_id,
                    workflow_id=row["workflow_id"],
                    status=WorkflowStatus(row["status"]),
                    trigger_type=row["trigger_type"],
                    trigger_payload=json.loads(row["trigger_payload_json"]),
                    started_at=_parse_dt(row["started_at"]) or datetime.now(timezone.utc),
                    completed_at=_parse_dt(row["completed_at"]),
                    duration_ms=row["duration_ms"],
                    step_runs=step_runs,
                    context=json.loads(row["context_json"]),
                    error=row["error"],
                )
            )
        return runs

    def close(self) -> None:
        """Close database connection."""
        self._conn.close()
