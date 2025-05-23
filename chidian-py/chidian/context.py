"""
Context utilities for controlling chidian behavior.

This module provides thread-local context management for controlling
how various chidian functions behave, particularly around strict mode.
"""

from contextlib import contextmanager
from typing import Generator
import threading


# Thread-local storage for context
_context = threading.local()


def get_context() -> dict:
    """Get the current context."""
    if not hasattr(_context, 'data'):
        _context.data = {}
    return _context.data


def set_context(**kwargs) -> None:
    """Set values in the current context."""
    context = get_context()
    context.update(kwargs)


def clear_context() -> None:
    """Clear the current context."""
    if hasattr(_context, 'data'):
        _context.data.clear()


@contextmanager
def mapping_context(**kwargs) -> Generator[None, None, None]:
    """
    Context manager for setting mapping options.
    
    Args:
        strict: If True, enables strict mode for mapping operations
        **kwargs: Additional context options
        
    Example:
        with mapping_context(strict=True):
            result = mapper(data)
    """
    # Save current context
    old_context = get_context().copy()
    
    try:
        # Set new context
        set_context(**kwargs)
        yield
    finally:
        # Restore old context
        clear_context()
        set_context(**old_context)


def is_strict_mode() -> bool:
    """Check if strict mode is currently enabled."""
    return get_context().get('strict', False) 