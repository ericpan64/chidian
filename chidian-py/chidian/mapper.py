"""
Mapper utilities for strict mode handling.
"""

from contextlib import contextmanager
from typing import Generator

# Global strict mode state
_strict_mode = False


def is_strict_mode() -> bool:
    """
    Check if strict mode is currently enabled.
    
    Returns:
        True if strict mode is enabled, False otherwise
    """
    return _strict_mode


def set_strict_mode(enabled: bool) -> None:
    """
    Enable or disable strict mode.
    
    Args:
        enabled: Whether to enable strict mode
    """
    global _strict_mode
    _strict_mode = enabled


@contextmanager
def mapping_context(strict: bool = False) -> Generator[None, None, None]:
    """
    Context manager for temporarily setting strict mode.
    
    Args:
        strict: Whether to enable strict mode within this context
        
    Yields:
        None
    """
    old_strict = _strict_mode
    set_strict_mode(strict)
    try:
        yield
    finally:
        set_strict_mode(old_strict) 