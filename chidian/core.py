"""
Core get/put functions for chidian data traversal and mutation.
"""

import copy
from typing import Any, Callable

from .lib.core_helpers import (
    apply_functions,
    mutate_path,
    traverse_path,
    validate_mutation_path,
)
from .lib.parser import parse_path


def get(
    source: dict | list,
    key: str,
    default: Any = None,
    apply: Callable | list[Callable] | None = None,
    strict: bool = False,
) -> Any:
    """
    Extract values from nested data structures using path notation.

    Args:
        source: Source data to traverse
        key: Path string (e.g., "data.items[0].name")
        default: Default value if path not found
        apply: Function(s) to apply to the result
        strict: If True, raise errors on missing paths

    Returns:
        Value at path or default if not found
    """
    try:
        path = parse_path(key)
    except ValueError as e:
        if strict:
            raise ValueError(f"Invalid path syntax: {key}") from e
        return default

    try:
        result = traverse_path(source, path, strict=strict)
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


def put(
    target: Any,
    path: str,
    value: Any,
    strict: bool = False,
) -> Any:
    """
    Set a value in a nested data structure, creating containers as needed.

    Args:
        target: Target data structure to modify
        path: Path string (e.g., "data.items[0].name")
        value: Value to set
        strict: If True, raise errors on invalid operations

    Returns:
        Modified copy of the target data
    """
    try:
        parsed_path = parse_path(path)
    except ValueError as e:
        raise ValueError(f"Invalid path syntax: {path}") from e

    # Validate path for mutation
    if not validate_mutation_path(parsed_path):
        if strict:
            raise ValueError(f"Invalid mutation path: {path}")
        return target

    # Deep copy for copy-on-write semantics
    result = copy.deepcopy(target)

    try:
        mutate_path(result, parsed_path, value, strict=strict)
    except Exception:
        if strict:
            raise
        return target

    return result
