"""
Helper functions for core get/put operations.
"""

from typing import Any, Callable

from .parser import Path, PathSegment, PathSegmentType


def traverse_path(data: Any, path: Path, strict: bool = False) -> Any:
    """Traverse data structure according to path."""
    current = [data]

    for segment in path.segments:
        next_items: list[Any] = []

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


def _traverse_slice(data: Any, start: int | None, end: int | None, strict: bool) -> Any:
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


def _traverse_tuple(data: Any, paths: list[Path], strict: bool) -> tuple:
    """Traverse multiple paths and return as tuple."""
    results = []
    for path in paths:
        result = traverse_path(data, path, strict=strict)
        results.append(result)
    return tuple(results)


def apply_functions(value: Any, functions: Callable | list[Callable]) -> Any:
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
    current: Any, key: str, segments: list[PathSegment], index: int, strict: bool
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
    current: Any, idx: int, segments: list[PathSegment], index: int, strict: bool
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
