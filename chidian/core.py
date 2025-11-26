"""
Core grab function for chidian data traversal.
"""

from typing import Any, Callable

from .lib.core_helpers import apply_functions, traverse_path
from .lib.parser import parse_path


def grab(
    source: dict | list,
    path: str,
    default: Any = None,
    apply: Callable | list[Callable] | None = None,
    strict: bool = False,
) -> Any:
    """
    Extract values from nested data structures using path notation.

    Args:
        source: Source data to traverse
        path: Path string (e.g., "data.items[0].name")
        default: Default value if path not found
        apply: Function(s) to apply to the result
        strict: If True, raise errors on missing paths

    Returns:
        Value at path or default if not found

    Examples:
        grab(d, "user.name")           # Nested access
        grab(d, "items[0]")            # List index
        grab(d, "items[-1]")           # Negative index
        grab(d, "users[*].name")       # Map over list
    """
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
        result = None

    # Handle default value
    if result is None and default is not None:
        result = default

    # Apply functions if provided
    if apply is not None and result is not None:
        result = apply_functions(result, apply)

    return result
