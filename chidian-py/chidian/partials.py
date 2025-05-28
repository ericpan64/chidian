"""
The `partials` module provides a set of standardized partial classes if you don't want to write a bunch of lambda function.

This makes it easier to standardize code and saves structure when exported to pure JSON.
"""

from typing import Any, Callable, Iterable, TypeVar
import operator
from functools import partial

from .chidian import get as _get

T = TypeVar('T')


def get(key: str, default: Any = None, apply: Any = None, strict: bool = False) -> Callable[[Any], Any]:
    """Create a partial function for get operations."""
    def get_partial(source):
        return _get(source, key, default=default, apply=apply, strict=strict)
    return get_partial


# Arithmetic operations using operator module
def add(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Add a value to the input."""
    if before:
        return partial(operator.add, value)
    else:
        return lambda x: operator.add(x, value)


def subtract(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Subtract a value from the input."""
    if before:
        return partial(operator.sub, value)
    else:
        return lambda x: operator.sub(x, value)


def multiply(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Multiply the input by a value."""
    if before:
        return partial(operator.mul, value)
    else:
        return lambda x: operator.mul(x, value)


def divide(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Divide the input by a value."""
    if before:
        return partial(operator.truediv, value)
    else:
        return lambda x: operator.truediv(x, value)


# Comparison operations using operator module
def equals(value: Any) -> Callable[[Any], bool]:
    """Check if input equals the given value."""
    return partial(operator.eq, value)


def not_equal(value: Any) -> Callable[[Any], bool]:
    """Check if input does not equal the given value."""
    return partial(operator.ne, value)


def equivalent(value: Any) -> Callable[[Any], bool]:
    """Check if input is the same object as the given value."""
    return partial(operator.is_, value)


def not_equivalent(value: Any) -> Callable[[Any], bool]:
    """Check if input is not the same object as the given value."""
    return partial(operator.is_not, value)


def contains(value: Any) -> Callable[[Any], bool]:
    """Check if input contains the given value."""
    return lambda x: operator.contains(x, value)


def not_contains(value: Any) -> Callable[[Any], bool]:
    """Check if input does not contain the given value."""
    return lambda x: not operator.contains(x, value)


def contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is contained in the given container."""
    return lambda x: operator.contains(container, x)


def not_contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is not contained in the given container."""
    return lambda x: not operator.contains(container, x)


def isinstance_of(type_or_types: type) -> Callable[[Any], bool]:
    """Check if input is an instance of the given type(s)."""
    return lambda x: isinstance(x, type_or_types)


# Iterable operations using operator module
def keep(n: int) -> Callable[[Iterable[T]], Iterable[T]]:
    """Keep only the first n items from an iterable."""
    return lambda x: x[:n]


def index(i: int) -> Callable[[Iterable[T]], T]:
    """Get the item at index i from an iterable."""
    return lambda x: operator.getitem(x, i)


# Standard library wrappers
def map_to_list(func: Callable[[T], Any]) -> Callable[[Iterable[T]], list]:
    """Apply a function to each item in an iterable and return a list."""
    return lambda iterable: list(map(func, iterable))


def filter_to_list(predicate: Callable[[T], bool]) -> Callable[[Iterable[T]], list]:
    """Filter an iterable using a predicate and return a list."""
    return lambda iterable: list(filter(predicate, iterable))