"""
The `partials` module provides a simplified set of core functions for data transformation.

This focuses on basic operations that are Rust-friendly and essential for data processing.
"""

import operator
from functools import partial, reduce
from typing import Any, Callable, TypeVar

from chidian_rs import get as _get  # type: ignore[attr-defined]

T = TypeVar("T")


class FunctionChain:
    """Composable function chain that consolidates operations."""

    def __init__(self, *operations: Callable):
        self.operations = list(operations)

    def __rshift__(
        self, other: Callable | "FunctionChain" | "ChainableFn"
    ) -> "FunctionChain":
        """Chain operations with >> operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*self.operations, *other.operations)
        elif isinstance(other, ChainableFn):
            return FunctionChain(*self.operations, other.func)
        else:
            return FunctionChain(*self.operations, other)

    def __call__(self, value: Any) -> Any:
        """Apply all operations in sequence."""
        return reduce(lambda v, f: f(v), self.operations, value)

    def __repr__(self) -> str:
        ops = " >> ".join(
            f.__name__ if hasattr(f, "__name__") else str(f) for f in self.operations
        )
        return f"FunctionChain({ops})"

    def __len__(self) -> int:
        """Number of operations in the chain."""
        return len(self.operations)


class ChainableFn:
    """Wrapper to make any function/partial chainable with >>."""

    def __init__(self, func: Callable):
        self.func = func
        # Preserve function metadata
        self.__name__ = getattr(func, "__name__", repr(func))
        self.__doc__ = getattr(func, "__doc__", None)

    def __rshift__(
        self, other: Callable | FunctionChain | "ChainableFn"
    ) -> FunctionChain:
        """Start or extend a chain with >> operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(self.func, *other.operations)
        elif isinstance(other, ChainableFn):
            return FunctionChain(self.func, other.func)
        else:
            return FunctionChain(self.func, other)

    def __rrshift__(self, other: Callable | FunctionChain) -> FunctionChain:
        """Allow chaining when ChainableFn is on the right side."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*other.operations, self.func)
        else:
            return FunctionChain(other, self.func)

    def __call__(self, *args, **kwargs):
        """Call the wrapped function."""
        return self.func(*args, **kwargs)

    def __repr__(self) -> str:
        return f"ChainableFn({self.__name__})"


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


# String manipulation functions as ChainableFn
upper = ChainableFn(str.upper)
lower = ChainableFn(str.lower)
strip = ChainableFn(str.strip)


def split(sep: str | None = None) -> ChainableFn:
    """Create a chainable split function."""
    return ChainableFn(partial(str.split, sep=sep))


def replace(old: str, new: str) -> ChainableFn:
    """Create a chainable replace function."""
    return ChainableFn(
        partial(
            lambda s, old_val, new_val: s.replace(old_val, new_val),
            old_val=old,
            new_val=new,
        )
    )


def join(sep: str) -> ChainableFn:
    """Create a chainable join function."""
    return ChainableFn(partial(lambda separator, items: separator.join(items), sep))


# Array/List operations as ChainableFn
first = ChainableFn(lambda x: x[0] if x else None)
last = ChainableFn(lambda x: x[-1] if x else None)
length = ChainableFn(len)


def at_index(i: int) -> ChainableFn:
    """Get element at index."""
    return ChainableFn(partial(lambda x, idx: x[idx] if len(x) > idx else None, idx=i))


def slice_range(start: int | None = None, end: int | None = None) -> ChainableFn:
    """Slice a sequence."""
    return ChainableFn(partial(lambda x, s, e: x[s:e], s=start, e=end))


# Type conversions as ChainableFn
to_int = ChainableFn(int)
to_float = ChainableFn(float)
to_str = ChainableFn(str)
to_bool = ChainableFn(bool)


# Utility functions
def round_to(decimals: int) -> ChainableFn:
    """Round to specified decimals."""
    return ChainableFn(partial(round, ndigits=decimals))


def default_to(default_value: Any) -> ChainableFn:
    """Replace None with default value."""
    return ChainableFn(
        partial(lambda x, default: default if x is None else x, default=default_value)
    )
