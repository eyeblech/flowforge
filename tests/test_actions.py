"""Tests for built-in action implementations."""

import pytest
from pathlib import Path
from flowforge.actions.base import ActionContext
from flowforge.actions.delay import DelayAction
from flowforge.actions.file import FileAction
from flowforge.actions.http import HttpAction
from flowforge.actions.notify import NotifyAction
from flowforge.actions.shell import ShellAction
from flowforge.actions.sql import SqlAction
from flowforge.actions.transform import TransformAction


@pytest.fixture
def dummy_context() -> ActionContext:
    return ActionContext(step_id="test_step", run_id="test_run", workflow_id="test_wf")


@pytest.mark.asyncio
async def test_shell_action_success(dummy_context: ActionContext):
    action = ShellAction()
    res = await action.execute({"command": "echo 'hello flowforge'"}, dummy_context)
    assert res.success is True
    assert res.output["stdout"] == "hello flowforge"
    assert res.output["exit_code"] == 0


@pytest.mark.asyncio
async def test_shell_action_failure(dummy_context: ActionContext):
    action = ShellAction()
    res = await action.execute({"command": "exit 42", "fail_on_error": True}, dummy_context)
    assert res.success is False
    assert res.output["exit_code"] == 42
    assert "code 42" in res.error


@pytest.mark.asyncio
async def test_transform_action(dummy_context: ActionContext):
    action = TransformAction()
    res = await action.execute({"value": {"computed": 100}}, dummy_context)
    assert res.success is True
    assert res.output == {"computed": 100}

    # Test list projection
    res_list = await action.execute({"items": [1, 2, 3, 4], "limit": 2}, dummy_context)
    assert res_list.output == [1, 2]


@pytest.mark.asyncio
async def test_file_action_crud(tmp_path: Path, dummy_context: ActionContext):
    action = FileAction()
    target_file = tmp_path / "test.txt"

    # 1. Write
    res_write = await action.execute(
        {"operation": "write", "path": str(target_file), "content": "Initial Line\n"},
        dummy_context,
    )
    assert res_write.success is True
    assert target_file.exists()

    # 2. Append
    res_append = await action.execute(
        {"operation": "append", "path": str(target_file), "content": "Second Line\n"},
        dummy_context,
    )
    assert res_append.success is True

    # 3. Read
    res_read = await action.execute(
        {"operation": "read", "path": str(target_file)}, dummy_context
    )
    assert res_read.success is True
    assert "Initial Line" in res_read.output["content"]
    assert "Second Line" in res_read.output["content"]

    # 4. Exists
    res_exists = await action.execute(
        {"operation": "exists", "path": str(target_file)}, dummy_context
    )
    assert res_exists.output["exists"] is True
    assert res_exists.output["is_file"] is True

    # 5. Delete
    res_del = await action.execute(
        {"operation": "delete", "path": str(target_file)}, dummy_context
    )
    assert res_del.success is True
    assert not target_file.exists()


@pytest.mark.asyncio
async def test_delay_action(dummy_context: ActionContext):
    action = DelayAction()
    res = await action.execute({"seconds": 0.05}, dummy_context)
    assert res.success is True
    assert res.output["slept_seconds"] == 0.05


@pytest.mark.asyncio
async def test_sql_action(tmp_path: Path, dummy_context: ActionContext):
    action = SqlAction()
    db_file = tmp_path / "test_sql.db"

    # Create table
    res_create = await action.execute(
        {
            "database": str(db_file),
            "query": "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT);",
            "fetch": False,
        },
        dummy_context,
    )
    assert res_create.success is True

    # Insert row
    res_insert = await action.execute(
        {
            "database": str(db_file),
            "query": "INSERT INTO items (name) VALUES (?);",
            "params": ["widget"],
            "fetch": False,
        },
        dummy_context,
    )
    assert res_insert.success is True

    # Query row
    res_query = await action.execute(
        {
            "database": str(db_file),
            "query": "SELECT * FROM items WHERE name = ?;",
            "params": ["widget"],
            "fetch": True,
        },
        dummy_context,
    )
    assert res_query.success is True
    assert len(res_query.output["rows"]) == 1
    assert res_query.output["rows"][0]["name"] == "widget"
