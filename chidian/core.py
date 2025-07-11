"""
Core get/put functions for chidian data traversal and mutation.
"""

import copy
from typing import Any, Callable, List, Optional, Union

from .parser import Path, PathSegment, PathSegmentType, parse_path


def get(
    source: Any,
    key: str,
    default: Any = None,
    apply: Optional[Union[Callable, List[Callable]]] = None,
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


def traverse_path(data: Any, path: Path, strict: bool = False) -> Any:
    """Traverse data structure according to path."""
    current = [data]

    for segment in path.segments:
        next_items: List[Any] = []

        for item in current:
            if item is None:
                if strict:
                    raise ValueError("Cannot traverse None value")
                next_items.append(None)
                continue

            if segment.type == PathSegmentType.KEY:
                assert isinstance(segment.value, str)
                result = _traverse_key(item, segment.value, strict)
                # Only extend if we applied key to a list of dicts
                # (i.e., when item was a list and we distributed the key)
                if isinstance(item, list) and isinstance(result, list):
                    next_items.extend(result)
                else:
                    next_items.append(result)

            elif segment.type == PathSegmentType.INDEX:
                assert isinstance(segment.value, int)
                result = _traverse_index(item, segment.value, strict)
                next_items.append(result)

            elif segment.type == PathSegmentType.SLICE:
                assert isinstance(segment.value, tuple)
                start, end = segment.value
                result = _traverse_slice(item, start, end, strict)
                next_items.append(result)

            elif segment.type == PathSegmentType.WILDCARD:
                result = _traverse_wildcard(item, strict)
                if isinstance(result, list):
                    next_items.extend(result)
                else:
                    next_items.append(result)

            elif segment.type == PathSegmentType.TUPLE:
                assert isinstance(segment.value, list)
                result = _traverse_tuple(item, segment.value, strict)
                next_items.append(result)

        current = next_items

    # Return single item if only one result
    if len(current) == 1:
        return current[0]
    return current


def _traverse_key(data: Any, key: str, strict: bool) -> Any:
    """Traverse a key in dict or list of dicts."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        elif strict:
            raise KeyError(f"Key '{key}' not found")
        else:
            return None

    elif isinstance(data, list):
        # Apply key to each dict in list
        results = []
        for item in data:
            if isinstance(item, dict):
                if key in item:
                    results.append(item[key])
                elif strict:
                    raise KeyError(f"Key '{key}' not found in list element")
                else:
                    results.append(None)
            elif strict:
                raise TypeError("Expected dict in list but got different type")
            else:
                results.append(None)
        return results

    elif strict:
        raise TypeError("Expected dict but got different type")
    else:
        return None


def _traverse_index(data: Any, idx: int, strict: bool) -> Any:
    """Traverse an index in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return None

    # Handle negative indexing
    length = len(data)
    actual_idx = idx if idx >= 0 else length + idx

    if 0 <= actual_idx < length:
        return data[actual_idx]
    elif strict:
        raise IndexError(f"Index {idx} out of range")
    else:
        return None


def _traverse_slice(
    data: Any, start: Optional[int], end: Optional[int], strict: bool
) -> Any:
    """Traverse a slice in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return None

    # Python handles negative indices and None values in slices automatically
    return data[start:end]


def _traverse_wildcard(data: Any, strict: bool) -> Any:
    """Traverse all elements in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return None
    return data


def _traverse_tuple(data: Any, paths: List[Path], strict: bool) -> tuple:
    """Traverse multiple paths and return as tuple."""
    results = []
    for path in paths:
        result = traverse_path(data, path, strict=strict)
        results.append(result)
    return tuple(results)


def apply_functions(value: Any, functions: Union[Callable, List[Callable]]) -> Any:
    """Apply a function or list of functions to a value."""
    if not isinstance(functions, list):
        functions = [functions]

    current = value
    for func in functions:
        try:
            current = func(current)
        except Exception:
            return None

    return current


def validate_mutation_path(path: Path) -> bool:
    """Validate that a path is suitable for mutation operations."""
    if not path.segments:
        return False

    # Path must start with a key (not an index)
    if path.segments[0].type != PathSegmentType.KEY:
        return False

    # Check for unsupported segment types
    for segment in path.segments:
        if segment.type in (
            PathSegmentType.WILDCARD,
            PathSegmentType.SLICE,
            PathSegmentType.TUPLE,
        ):
            return False

    return True


def mutate_path(data: Any, path: Path, value: Any, strict: bool = False) -> None:
    """Mutate data in-place at the specified path."""
    if not path.segments:
        raise ValueError("Empty path")

    # Navigate to parent of target
    current = data
    for i, segment in enumerate(path.segments[:-1]):
        if segment.type == PathSegmentType.KEY:
            assert isinstance(segment.value, str)
            current = _ensure_key_container(
                current, segment.value, path.segments, i, strict
            )
        elif segment.type == PathSegmentType.INDEX:
            assert isinstance(segment.value, int)
            current = _ensure_index_container(
                current, segment.value, path.segments, i, strict
            )

    # Set final value
    final_segment = path.segments[-1]
    if final_segment.type == PathSegmentType.KEY:
        assert isinstance(final_segment.value, str)
        if not isinstance(current, dict):
            if strict:
                raise TypeError(f"Cannot set key '{final_segment.value}' on non-dict")
            return
        current[final_segment.value] = value

    elif final_segment.type == PathSegmentType.INDEX:
        assert isinstance(final_segment.value, int)
        if not isinstance(current, list):
            if strict:
                raise TypeError(f"Cannot set index {final_segment.value} on non-list")
            return

        idx = final_segment.value
        # Expand list if needed for positive indices
        if idx >= 0:
            while len(current) <= idx:
                current.append(None)
            current[idx] = value
        else:
            # Negative index
            actual_idx = len(current) + idx
            if actual_idx < 0:
                if strict:
                    raise IndexError(f"Index {idx} out of range")
            else:
                current[actual_idx] = value


def _ensure_key_container(
    current: Any, key: str, segments: List[PathSegment], index: int, strict: bool
) -> Any:
    """Ensure a dict exists at key, creating if needed."""
    if not isinstance(current, dict):
        if strict:
            raise TypeError(f"Cannot traverse into non-dict at '{key}'")
        return current

    # Determine what type of container we need
    next_segment = segments[index + 1]
    container_type = _determine_container_type(next_segment)

    if key not in current:
        # Create appropriate container
        if container_type == "list":
            current[key] = []
        else:
            current[key] = {}
    else:
        # Validate existing container type
        existing = current[key]
        if container_type == "list" and not isinstance(existing, list):
            if strict:
                raise TypeError(
                    f"Expected list at '{key}' but found {type(existing).__name__}"
                )
            current[key] = []
        elif container_type == "dict" and not isinstance(existing, dict):
            if strict:
                raise TypeError(
                    f"Expected dict at '{key}' but found {type(existing).__name__}"
                )
            current[key] = {}

    return current[key]


def _ensure_index_container(
    current: Any, idx: int, segments: List[PathSegment], index: int, strict: bool
) -> Any:
    """Ensure a list exists and has capacity for index."""
    if not isinstance(current, list):
        if strict:
            raise TypeError("Cannot index into non-list")
        return current

    # Handle negative indexing
    actual_idx = idx if idx >= 0 else len(current) + idx
    if actual_idx < 0:
        if strict:
            raise IndexError(f"Index {idx} out of range")
        return current

    # Expand list if needed
    while len(current) <= actual_idx:
        current.append(None)

    # Determine container type for this index
    next_segment = segments[index + 1]
    container_type = _determine_container_type(next_segment)

    if current[actual_idx] is None:
        # Create appropriate container
        if container_type == "list":
            current[actual_idx] = []
        else:
            current[actual_idx] = {}
    else:
        # Validate existing container type
        existing = current[actual_idx]
        if container_type == "list" and not isinstance(existing, list):
            if strict:
                raise TypeError(
                    f"Expected list at index {idx} but found {type(existing).__name__}"
                )
            current[actual_idx] = []
        elif container_type == "dict" and not isinstance(existing, dict):
            if strict:
                raise TypeError(
                    f"Expected dict at index {idx} but found {type(existing).__name__}"
                )
            current[actual_idx] = {}

    return current[actual_idx]


def _determine_container_type(segment: PathSegment) -> str:
    """Determine whether we need a dict or list container."""
    if segment.type == PathSegmentType.INDEX:
        return "list"
    return "dict"
