"""Tests for Typer CLI commands."""

import pytest
from typer.testing import CliRunner
from flowforge.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "FlowForge" in result.stdout
    assert "run" in result.stdout
    assert "validate" in result.stdout


def test_cli_actions():
    result = runner.invoke(app, ["actions"])
    assert result.exit_code == 0
    assert "Registered FlowForge Actions" in result.stdout
    assert "http" in result.stdout
    assert "shell" in result.stdout
    assert "sql" in result.stdout


def test_cli_validate_valid():
    result = runner.invoke(app, ["validate", "examples/02_system_health_watchdog.yaml"])
    assert result.exit_code == 0
    assert "is valid" in result.stdout


def test_cli_tree():
    result = runner.invoke(app, ["tree", "examples/05_parallel_dag_fanout.yaml"])
    assert result.exit_code == 0
    assert "Parallel DAG Fan-Out" in result.stdout


def test_cli_run():
    result = runner.invoke(app, ["run", "examples/02_system_health_watchdog.yaml"])
    assert result.exit_code == 0
    assert "SUCCESS" in result.stdout


def test_cli_runs_list():
    result = runner.invoke(app, ["runs", "list"])
    assert result.exit_code == 0
