"""
The @mapper decorator for transforming functions into data mappers.
"""

from functools import wraps
from typing import Callable, ParamSpec, TypeVar, overload

from .process import process_output

P = ParamSpec("P")
R = TypeVar("R")


@overload
def mapper(_func: Callable[P, R], *, remove_empty: bool = True) -> Callable[P, R]: ...


@overload
def mapper(
    _func: None = None, *, remove_empty: bool = True
) -> Callable[[Callable[P, R]], Callable[P, R]]: ...


def mapper(
    _func: Callable[P, R] | None = None, *, remove_empty: bool = True
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """
    Decorator that transforms a mapping function into a callable mapper.

    The decorated function should return a dict. The decorator automatically:
    - Processes DROP sentinels (removes marked values/containers)
    - Unwraps KEEP wrappers (preserves explicitly kept values)
    - Removes empty values by default ({}, [], "", None)

    Can be used with or without arguments:
        @mapper
        def my_mapping(d): ...

        @mapper(remove_empty=False)
        def my_mapping(d): ...

    Args:
        remove_empty: If True (default), remove empty values from output.
                     KEEP-wrapped values are always preserved.

    Returns:
        Decorated function that processes its output through the mapper pipeline.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            # Call the original function to get the raw mapping result
            result = func(*args, **kwargs)

            # Process the result (DROP, KEEP, empty removal)
            return process_output(result, remove_empty=remove_empty)

        return wrapper

    # Handle both @mapper and @mapper(...) syntax
    if _func is not None:
        # Called as @mapper without parentheses
        return decorator(_func)
    else:
        # Called as @mapper(...) with arguments
        return decorator
