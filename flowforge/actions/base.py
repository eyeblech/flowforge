"""Base classes and registry for workflow actions."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Type
from pydantic import BaseModel, ConfigDict, Field


class ActionContext(BaseModel):
    """Contextual metadata and variables supplied to an executing action."""
    step_id: str
    run_id: str
    workflow_id: str
    context: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ActionResult(BaseModel):
    """Outcome and artifacts produced by an action execution."""
    success: bool = True
    output: Any = None
    error: Optional[str] = None
    logs: List[str] = Field(default_factory=list)


class BaseAction(ABC):
    """Abstract base class for all FlowForge step actions."""

    name: str = "base"

    @abstractmethod
    async def execute(self, params: Dict[str, Any], context: ActionContext) -> ActionResult:
        """Execute the action asynchronously with resolved parameters.
        
        Args:
            params: Dictionary of evaluated step inputs.
            context: ActionContext with execution metadata and variables.
            
        Returns:
            ActionResult with success flag, output payload, error, and logs.
        """
        pass


class ActionRegistry:
    """Registry maintaining available action implementations."""

    def __init__(self) -> None:
        self._actions: Dict[str, Type[BaseAction]] = {}

    def register(self, name: str) -> Callable[[Type[BaseAction]], Type[BaseAction]]:
        """Decorator to register an action class under a specific name."""
        def decorator(cls: Type[BaseAction]) -> Type[BaseAction]:
            cls.name = name
            self._actions[name] = cls
            return cls
        return decorator

    def get(self, name: str) -> Optional[Type[BaseAction]]:
        """Retrieve an action class by name."""
        return self._actions.get(name)

    def list_actions(self) -> List[str]:
        """Return list of all registered action names."""
        return sorted(list(self._actions.keys()))


# Global default registry instance
registry = ActionRegistry()
register_action = registry.register
