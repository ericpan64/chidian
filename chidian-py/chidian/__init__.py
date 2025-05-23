"""
Chidian - Functional programming utilities for nested data structures.

This package provides utilities for working with nested dictionaries and lists,
including partial function application, data extraction, and transformation.
"""

from . import partials
from .dicts import get
from .mapper import Mapper
from .context import mapping_context

# Import types from Python modules
from .lib.types import (
    DROP,
    KEEP,
    DropLevel,
    DropSentinel,
    Keep
)

__version__ = "0.1.0"
__all__ = [
    "partials",
    "get",
    "Mapper",
    "mapping_context",
    "DROP",
    "KEEP",
    "DropLevel",
    "DropSentinel",
    "Keep"
]
