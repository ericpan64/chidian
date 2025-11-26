"""
Helper functions for core grab operations.
"""

from typing import Any, Callable

from .parser import Path, PathSegmentType


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
