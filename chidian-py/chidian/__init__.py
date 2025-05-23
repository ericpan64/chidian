"""
Chidian - Functional programming utilities for nested data structures.

This package provides utilities for working with nested dictionaries and lists,
including partial function application, data extraction, and transformation.
"""

from . import partials
from .dict_utils import get
from .mapper import Mapper

__version__ = "0.1.0"
__all__ = ["partials", "get", "Mapper"]
