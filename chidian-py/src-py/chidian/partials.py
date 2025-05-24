"""
Partial function utilities for working with nested data structures.

This module provides utilities for creating partial functions and transformations
that can be used with the get() function and Mapper class.
"""

from typing import Any, Callable, Iterable, Union
from functools import partial
import operator
from . import chidian  # The compiled Rust module


def get(
    key: str,
    default: Any = None,
    apply: Union[Callable, Iterable[Callable], None] = None
) -> Callable[[Union[dict, list]], Any]:
    """
    Create a function that extracts values from nested data structures.
    
    Args:
        key: Dot-separated path to the value (e.g., "data.patient.id")
        default: Value to return if key is not found
        apply: Function or iterable of functions to apply to the result
        
    Returns:
        A function that takes a source and returns the extracted value
    """
    def _get(source: Union[dict, list]) -> Any:
        # Use the Rust implementation
        result = chidian.get(
            source=source,
            key=key,
            default=default,
            apply=apply,
            only_if=None,
            _drop_level=None,
            flatten=False,
            strict=None
        )
        
        # If the result is the default value and we have apply functions,
        # we need to apply them to the default since the Rust implementation
        # might not be doing this correctly
        if result == default and apply is not None and default is not None:
            if callable(apply):
                return apply(default)
            elif hasattr(apply, '__iter__'):
                current = default
                for func in apply:
                    current = func(current)
                return current
        
        return result
    return _get


def do(func: Callable, *args, **kwargs) -> Callable:
    """
    Create a partial function application.
    
    Unlike functools.partial, this applies the input as the first argument,
    followed by the provided arguments.
    
    Args:
        func: The function to partially apply
        *args: Positional arguments to pre-apply after the input
        **kwargs: Keyword arguments to pre-apply
        
    Returns:
        A new function that takes input as first arg, then applies provided args
    """
    def wrapper(input_arg):
        return func(input_arg, *args, **kwargs)
    return wrapper


def add(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Create a function that adds a value."""
    if before:
        return lambda x: value + x
    return lambda x: x + value


def subtract(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Create a function that subtracts a value."""
    if before:
        return lambda x: value - x
    return lambda x: x - value


def multiply(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Create a function that multiplies by a value."""
    if before:
        return lambda x: x * value  # Note: when before=True, we still do x * value for consistency
    return lambda x: x * value


def divide(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Create a function that divides by a value."""
    if before:
        return lambda x: value / x
    return lambda x: x / value


def equals(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks equality."""
    return lambda x: x == value


def not_equal(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks inequality."""
    return lambda x: x != value


def equivalent(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks identity (is)."""
    return lambda x: x is value


def not_equivalent(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks non-identity (is not)."""
    return lambda x: x is not value


def contains(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks if the argument contains a value."""
    return lambda x: value in x


def not_contains(value: Any) -> Callable[[Any], bool]:
    """Create a function that checks if the argument does not contain a value."""
    return lambda x: value not in x


def contained_in(container: Any) -> Callable[[Any], bool]:
    """Create a function that checks if a value is contained in the given container."""
    return lambda x: x in container


def not_contained_in(container: Any) -> Callable[[Any], bool]:
    """Create a function that checks if a value is not contained in the given container."""
    return lambda x: x not in container


def isinstance_of(type_or_types: Union[type, tuple]) -> Callable[[Any], bool]:
    """Create a function that checks if a value is an instance of given type(s)."""
    return lambda x: isinstance(x, type_or_types)


def keep(n: int) -> Callable[[Union[list, tuple]], Union[list, tuple]]:
    """Create a function that keeps the first n elements of a sequence."""
    return lambda x: x[:n]


def index(i: int) -> Callable[[Union[list, tuple]], Any]:
    """Create a function that returns the element at index i."""
    return lambda x: x[i]


def map_to_list(func: Callable) -> Callable[[Iterable], list]:
    """Create a function that maps a function over an iterable and returns a list."""
    return lambda x: list(map(func, x))


def filter_to_list(func: Callable) -> Callable[[Iterable], list]:
    """Create a function that filters an iterable and returns a list."""
    return lambda x: list(filter(func, x))
