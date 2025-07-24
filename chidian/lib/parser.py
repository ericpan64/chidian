"""
Path parser for chidian path expressions - now using PEG grammar.

This module provides the core data structures and exports the PEG parser
as the primary parser implementation.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Union


class PathSegmentType(Enum):
    KEY = auto()
    INDEX = auto()
    SLICE = auto()
    WILDCARD = auto()
    TUPLE = auto()


@dataclass
class PathSegment:
    """Represents a single segment in a path."""

    type: PathSegmentType
    value: Union[str, int, tuple[Optional[int], Optional[int]], List["Path"]]

    @classmethod
    def key(cls, name: str) -> "PathSegment":
        return cls(PathSegmentType.KEY, name)

    @classmethod
    def index(cls, idx: int) -> "PathSegment":
        return cls(PathSegmentType.INDEX, idx)

    @classmethod
    def slice(cls, start: Optional[int], end: Optional[int]) -> "PathSegment":
        return cls(PathSegmentType.SLICE, (start, end))

    @classmethod
    def wildcard(cls) -> "PathSegment":
        return cls(PathSegmentType.WILDCARD, "*")

    @classmethod
    def tuple(cls, paths: List["Path"]) -> "PathSegment":
        return cls(PathSegmentType.TUPLE, paths)


@dataclass
class Path:
    """Represents a parsed path expression."""

    segments: List[PathSegment]


# Export the PEG parser as the main parser
try:
    from .get_dsl_parser import parse_path_peg as parse_path
except ImportError:
    # Fallback if PEG parser isn't available
    def parse_path(path_str: str) -> Path:
        raise NotImplementedError("PEG parser not available")


__all__ = ["Path", "PathSegment", "PathSegmentType", "parse_path"]
