"""
Core grab function for chidian data traversal.
"""

from typing import Any, Callable

from .context import is_strict
from .lib.core_helpers import MISSING, apply_functions, traverse_path
from .lib.parser import parse_path


def grab(
    source: dict | list,
    path: str,
    default: Any = None,
    apply: Callable | list[Callable] | None = None,
) -> Any:
    """
    Extract values from nested data structures using path notation.

    Args:
        source: Source data to traverse
        path: Path string (e.g., "data.items[0].name")
        default: Default value if path not found. An existing key whose
                 value is None is returned as None, not replaced by default.
        apply: Function(s) to apply to the result. In non-strict mode a
               function that raises yields None; in strict mode it raises.

    Returns:
        Value at path or default if not found. Paths that fan out over a
        list (e.g. "users[*].name") always return a list.

    Raises:
        KeyError: In strict mode, if a dict key is not found
        IndexError: In strict mode, if a list index is out of range
        TypeError: In strict mode, if a type mismatch occurs during traversal
        Exception: In strict mode, anything raised by an `apply` function

    Note:
        Strict mode distinguishes between "key not found" and "key exists with None":
        - {"has_none": None} -> grab(d, "has_none") returns None (OK in strict mode)
        - {} -> grab(d, "missing") raises KeyError in strict mode

    Examples:
        grab(d, "user.name")           # Nested access
        grab(d, "items[0]")            # List index
        grab(d, "items[-1]")           # Negative index
        grab(d, "users[*].name")       # Map over list
    """
    strict = is_strict()

    try:
        parsed = parse_path(path)
    except ValueError as e:
        if strict:
            raise ValueError(f"Invalid path syntax: {path}") from e
        return default

    try:
        result = traverse_path(source, parsed, strict=strict)
    except Exception:
        if strict:
            raise
        result = MISSING

    # Handle default value (only when the path doesn't exist)
    if result is MISSING:
        result = default

    # Apply functions if provided
    if apply is not None and result is not None:
        result = apply_functions(result, apply, strict=strict)

    return result
