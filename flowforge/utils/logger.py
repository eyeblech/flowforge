"""Structured logging configuration for FlowForge."""

import logging
import sys
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler

_console: Optional[Console] = None


def get_console() -> Console:
    """Return the shared Rich console instance."""
    global _console
    if _console is None:
        _console = Console()
    return _console


def setup_logger(
    name: str = "flowforge",
    level: int = logging.INFO,
    use_rich: bool = True
) -> logging.Logger:
    """Configure and return a structured logger."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers on re-entry
    if not logger.handlers:
        if use_rich:
            handler = RichHandler(
                console=get_console(),
                rich_tracebacks=True,
                show_time=True,
                show_path=False,
                markup=True,
            )
        else:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False

    return logger


logger = setup_logger()
