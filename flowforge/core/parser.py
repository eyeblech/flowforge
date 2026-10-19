"""Workflow parser and schema validator."""

import json
from pathlib import Path
from typing import Any, Dict, Union
import yaml
from flowforge.core.graph import WorkflowGraph
from flowforge.core.models import WorkflowDefinition


class WorkflowParseError(Exception):
    """Raised when parsing or validating workflow syntax fails."""
    pass


def parse_workflow_dict(data: Dict[str, Any]) -> WorkflowDefinition:
    """Validate and convert dictionary data into a WorkflowDefinition."""
    try:
        workflow = WorkflowDefinition.model_validate(data)
    except Exception as e:
        raise WorkflowParseError(f"Workflow schema validation error: {e}") from e

    # Perform DAG cycle and reference validation
    WorkflowGraph(workflow)
    return workflow


def parse_workflow_str(content: str) -> WorkflowDefinition:
    """Parse workflow definition from YAML or JSON string."""
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise WorkflowParseError(f"Invalid YAML syntax: {e}") from e

    if not isinstance(data, dict):
        raise WorkflowParseError("Workflow document must be a YAML/JSON mapping/object.")

    return parse_workflow_dict(data)


def load_workflow_file(file_path: Union[str, Path]) -> WorkflowDefinition:
    """Load and parse workflow definition from a YAML or JSON file."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Workflow file not found: {path}")

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        raise WorkflowParseError(f"Failed to read workflow file {path}: {e}") from e

    return parse_workflow_str(content)
