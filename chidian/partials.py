"""
The `partials` module provides a simplified set of core functions for data transformation.

This focuses on basic operations that are Rust-friendly and essential for data processing.
"""

import operator
from functools import partial, reduce
from typing import Any, Callable, TypeVar

from .core import get as _get

T = TypeVar("T")


class FunctionChain:
    """Composable function chain that consolidates operations."""

    def __init__(self, *operations: Callable):
        self.operations = list(operations)

    def __or__(
        self, other: Callable | "FunctionChain" | "ChainableFunction"
    ) -> "FunctionChain":
        """Chain operations with | operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*self.operations, *other.operations)
        elif isinstance(other, ChainableFunction):
            return FunctionChain(*self.operations, other.func)
        else:
            return FunctionChain(*self.operations, other)

    def __call__(self, value: Any) -> Any:
        """Apply all operations in sequence."""
        return reduce(lambda v, f: f(v), self.operations, value)

    def __repr__(self) -> str:
        ops = " | ".join(
            f.__name__ if hasattr(f, "__name__") else str(f) for f in self.operations
        )
        return f"FunctionChain({ops})"

    def __len__(self) -> int:
        """Number of operations in the chain."""
        return len(self.operations)


class ChainableFunction:
    """Wrapper to make any function/partial chainable with |."""

    def __init__(self, func: Callable):
        self.func = func
        # Preserve function metadata
        self.__name__ = getattr(func, "__name__", repr(func))
        self.__doc__ = getattr(func, "__doc__", None)

    def __or__(
        self, other: Callable | FunctionChain | "ChainableFunction"
    ) -> FunctionChain:
        """Start or extend a chain with | operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(self.func, *other.operations)
        elif isinstance(other, ChainableFunction):
            return FunctionChain(self.func, other.func)
        else:
            return FunctionChain(self.func, other)

    def __ror__(self, other: Callable | FunctionChain) -> FunctionChain:
        """Allow chaining when ChainableFunction is on the right side."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*other.operations, self.func)
        else:
            return FunctionChain(other, self.func)

    def __call__(self, *args, **kwargs):
        """Call the wrapped function."""
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"ChainableFunction({self.__name__})"


def get(
    key: str, default: Any = None, apply: Any = None, strict: bool = False
) -> Callable[[Any], Any]:
    """Create a partial function for get operations."""

    def get_partial(source):
        return _get(source, key, default=default, apply=apply, strict=strict)

    return get_partial


# Arithmetic operations
def add(value: Any) -> Callable[[Any], Any]:
    """Add a value to the input."""
    return partial(lambda x, v: operator.add(x, v), v=value)


def subtract(value: Any) -> Callable[[Any], Any]:
    """Subtract a value from the input."""
    return partial(lambda x, v: operator.sub(x, v), v=value)


def multiply(value: Any) -> Callable[[Any], Any]:
    """Multiply the input by a value."""
    return partial(lambda x, v: operator.mul(x, v), v=value)


def divide(value: Any) -> Callable[[Any], Any]:
    """Divide the input by a value."""
    return partial(lambda x, v: operator.truediv(x, v), v=value)


# Boolean operations
def equals(value: Any) -> Callable[[Any], bool]:
    """Check if input equals the given value."""
    return partial(operator.eq, value)


def contains(value: Any) -> Callable[[Any], bool]:
    """Check if input contains the given value."""
    return partial(lambda x, v: operator.contains(x, v), v=value)


def isinstance_of(type_or_types: type) -> Callable[[Any], bool]:
    """Check if input is an instance of the given type(s)."""
    return partial(lambda x, types: isinstance(x, types), types=type_or_types)


# String manipulation functions as ChainableFunction
upper = ChainableFunction(str.upper)
lower = ChainableFunction(str.lower)
strip = ChainableFunction(str.strip)


def split(sep: str | None = None) -> ChainableFunction:
    """Create a chainable split function."""
    return ChainableFunction(partial(str.split, sep=sep))


def replace(old: str, new: str) -> ChainableFunction:
    """Create a chainable replace function."""
    return ChainableFunction(
        partial(
            lambda s, old_val, new_val: s.replace(old_val, new_val),
            old_val=old,
            new_val=new,
        )
    )


def join(sep: str) -> ChainableFunction:
    """Create a chainable join function."""
    return ChainableFunction(
        partial(lambda separator, items: separator.join(items), sep)
    )


# Array/List operations as ChainableFunction
first = ChainableFunction(lambda x: x[0] if x else None)
last = ChainableFunction(lambda x: x[-1] if x else None)
length = ChainableFunction(len)


def at_index(i: int) -> ChainableFunction:
    """Get element at index."""
    return ChainableFunction(
        partial(lambda x, idx: x[idx] if len(x) > idx else None, idx=i)
    )


def slice_range(start: int | None = None, end: int | None = None) -> ChainableFunction:
    """Slice a sequence."""
    return ChainableFunction(partial(lambda x, s, e: x[s:e], s=start, e=end))


# Type conversions as ChainableFunction
to_int = ChainableFunction(int)
to_float = ChainableFunction(float)
to_str = ChainableFunction(str)
to_bool = ChainableFunction(bool)


# Utility functions
def round_to(decimals: int) -> ChainableFunction:
    """Round to specified decimals."""
    return ChainableFunction(partial(round, ndigits=decimals))


def default_to(default_value: Any) -> ChainableFunction:
    """Replace None with default value."""
    return ChainableFunction(
        partial(lambda x, default: default if x is None else x, default=default_value)
    )
