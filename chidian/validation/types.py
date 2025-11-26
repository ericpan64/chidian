"""
Type definitions for chidian validation.

Provides a minimal Result type (Ok/Err) and type aliases.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
E = TypeVar("E")


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """Success result containing a value."""

    value: T

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False


@dataclass(frozen=True, slots=True)
class Err(Generic[E]):
    """Error result containing an error value."""

    error: E

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True


# Type aliases
CheckFn = Callable[[Any], bool]
Path = tuple[str | int, ...]
ValidationError = tuple[Path, str]
ValidationErrors = list[ValidationError]
