"""Tests for YAML/JSON workflow parser and validator."""

import pytest
from pathlib import Path
from flowforge.core.parser import (
    WorkflowParseError,
    load_workflow_file,
    parse_workflow_str,
)


def test_parse_valid_yaml():
    yaml_content = """
id: sample_wf
name: Sample Workflow
version: "1.0"
steps:
  - id: step_a
    action: shell
    with:
      command: "echo 1"
  - id: step_b
    action: shell
    depends_on: [step_a]
    with:
      command: "echo 2"
"""
    wf = parse_workflow_str(yaml_content)
    assert wf.id == "sample_wf"
    assert len(wf.steps) == 2
    assert wf.steps[1].depends_on == ["step_a"]


def test_parse_invalid_yaml_syntax():
    invalid_yaml = """
id: bad_yaml
name: Unclosed quote"
  steps:
"""
    with pytest.raises(WorkflowParseError):
        parse_workflow_str(invalid_yaml)


def test_parse_cyclic_yaml_raises_error():
    cycle_yaml = """
id: cyclic_wf
name: Cyclic Workflow
steps:
  - id: step_1
    action: shell
    depends_on: [step_2]
  - id: step_2
    action: shell
    depends_on: [step_1]
"""
    with pytest.raises(Exception):
        parse_workflow_str(cycle_yaml)


def test_load_workflow_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_workflow_file("/non/existent/path/workflow.yaml")
