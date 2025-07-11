"""
Path parser for chidian path expressions.

Supports:
- Simple keys: "data.patient.id"
- Array indices: "items[0]", "items[-1]"
- Slices: "items[1:3]", "items[:2]", "items[1:]"
- Wildcards: "items[*]"
- Tuples: "(id,name)", "(id,patient.name)"
"""

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional, Union


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
    value: Union[str, int, tuple[Optional[int], Optional[int]], list["Path"]]

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
    def tuple(cls, paths: list["Path"]) -> "PathSegment":
        return cls(PathSegmentType.TUPLE, paths)


@dataclass
class Path:
    """Represents a parsed path expression."""

    segments: list[PathSegment]


class PathParser:
    """Parser for chidian path expressions."""

    # Regex patterns
    KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*")
    INDEX_PATTERN = re.compile(r"^\[(-?\d+)\]")
    WILDCARD_PATTERN = re.compile(r"^\[\*\]")
    SLICE_PATTERN = re.compile(r"^\[(-?\d+)?:(-?\d+)?\]")

    def parse(self, path_str: str) -> Path:
        """Parse a path string into a Path object."""
        if not path_str:
            raise ValueError("Empty path")

        # Handle paths starting with brackets (e.g., "[0].name")
        segments = []
        remaining = path_str

        while remaining:
            # Try to parse a segment
            segment, rest = self._parse_segment(remaining)
            if segment is None:
                raise ValueError(f"Invalid path syntax at: {remaining}")

            # Handle case where multiple segments are returned (key[bracket] patterns)
            if isinstance(segment, list):
                segments.extend(segment)
            else:
                segments.append(segment)
            remaining = rest

            # Skip dot separator if present
            if remaining and remaining[0] == ".":
                remaining = remaining[1:]

        return Path(segments)

    def _parse_segment(
        self, s: str
    ) -> tuple[Union[PathSegment, list[PathSegment], None], str]:
        """Parse a single segment from the start of string s."""
        # Try wildcard first (most specific bracket pattern)
        if match := self.WILDCARD_PATTERN.match(s):
            return PathSegment.wildcard(), s[match.end() :]

        # Try slice
        if match := self.SLICE_PATTERN.match(s):
            start_str, end_str = match.groups()
            start = int(start_str) if start_str else None
            end = int(end_str) if end_str else None
            return PathSegment.slice(start, end), s[match.end() :]

        # Try index
        if match := self.INDEX_PATTERN.match(s):
            idx = int(match.group(1))
            return PathSegment.index(idx), s[match.end() :]

        # Try tuple
        if s.startswith("("):
            return self._parse_tuple(s)

        # Try key with optional brackets
        if match := self.KEY_PATTERN.match(s):
            key = match.group(0)
            rest = s[match.end() :]

            # Check for following brackets
            segments = [PathSegment.key(key)]
            while rest and rest[0] == "[":
                # Parse bracket expression
                if bracket_match := self.WILDCARD_PATTERN.match(rest):
                    segments.append(PathSegment.wildcard())
                    rest = rest[bracket_match.end() :]
                elif bracket_match := self.SLICE_PATTERN.match(rest):
                    start_str, end_str = bracket_match.groups()
                    start = int(start_str) if start_str else None
                    end = int(end_str) if end_str else None
                    segments.append(PathSegment.slice(start, end))
                    rest = rest[bracket_match.end() :]
                elif bracket_match := self.INDEX_PATTERN.match(rest):
                    idx = int(bracket_match.group(1))
                    segments.append(PathSegment.index(idx))
                    rest = rest[bracket_match.end() :]
                else:
                    break

            # Return all segments if we parsed brackets after the key
            if len(segments) == 1:
                return segments[0], rest
            else:
                # We have multiple segments from key[bracket] patterns
                # Return them all as a special case
                return segments, rest

        return None, s

    def _parse_tuple(self, s: str) -> tuple[Optional[PathSegment], str]:
        """Parse a tuple expression like (id,name) or (id,patient.name)."""
        if not s.startswith("("):
            return None, s

        # Find matching closing paren
        paren_count = 0
        end_pos = -1
        for i, ch in enumerate(s):
            if ch == "(":
                paren_count += 1
            elif ch == ")":
                paren_count -= 1
                if paren_count == 0:
                    end_pos = i
                    break

        if end_pos == -1:
            raise ValueError("Unmatched parenthesis in tuple")

        # Extract content between parens
        content = s[1:end_pos].strip()
        if not content:
            raise ValueError("Empty tuple")

        # Split by comma (simple split for now)
        # TODO: Handle nested commas in paths
        parts = [p.strip() for p in content.split(",")]
        paths = []

        for part in parts:
            path = self.parse(part)
            paths.append(path)

        return PathSegment.tuple(paths), s[end_pos + 1 :]


def parse_path(path_str: str) -> Path:
    """Convenience function to parse a path string."""
    parser = PathParser()
    return parser.parse(path_str)
