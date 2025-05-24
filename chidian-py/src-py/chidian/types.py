"""
Type definitions for chidian package.

Provides sentinel objects and types for controlling data structure operations.
"""

from typing import Any, Union
from enum import Enum


class DropLevel(Enum):
    """Enumeration of drop levels for removing objects at different nesting levels."""
    THIS_OBJECT = "THIS_OBJECT"
    PARENT = "PARENT"
    GRANDPARENT = "GRANDPARENT"
    GREATGRANDPARENT = "GREATGRANDPARENT"


class DropSentinel:
    """Sentinel class for marking objects to be dropped during mapping operations."""
    
    THIS_OBJECT = DropLevel.THIS_OBJECT
    PARENT = DropLevel.PARENT
    GRANDPARENT = DropLevel.GRANDPARENT
    GREATGRANDPARENT = DropLevel.GREATGRANDPARENT


class Keep:
    """Wrapper class for explicitly keeping values that would normally be removed as empty."""
    
    def __init__(self, value: Any):
        self.value = value
    
    def __repr__(self) -> str:
        return f"Keep({self.value!r})"
    
    def __eq__(self, other) -> bool:
        if isinstance(other, Keep):
            return self.value == other.value
        return False


# Singleton instances
DROP = DropSentinel()
KEEP = Keep

__all__ = [
    "DROP",
    "KEEP", 
    "DropLevel",
    "DropSentinel",
    "Keep"
] 