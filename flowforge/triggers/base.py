"""Base interface for background workflow triggers."""

from abc import ABC, abstractmethod


class BaseTrigger(ABC):
    """Abstract trigger manager interface."""

    @abstractmethod
    async def start(self) -> None:
        """Start listening for trigger events."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for trigger events."""
        pass
