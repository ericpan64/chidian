"""
Helper functions for core grab operations.
"""

from typing import Any, Callable

from .parser import Path, PathSegmentType


class _Missing:
    """Sentinel for a path that does not exist (as opposed to an explicit None)."""

    def __repr__(self) -> str:
        return "MISSING"


MISSING: Any = _Missing()


def traverse_path(data: Any, path: Path, strict: bool = False) -> Any:
    """
    Traverse data structure according to path.

    Returns MISSING if the path does not exist (non-strict mode only).
    Paths that fan out over a list (`[*]`, or a key applied to a list) always
    return a list, with missing elements as None.
    """
    current = [data]
    fanned_out = False

    for segment in path.segments:
        next_items: list[Any] = []

        for item in current:
            if item is None or item is MISSING:
                if strict:
                    raise ValueError("Cannot traverse None value")
                next_items.append(MISSING)
                continue

            if segment.type == PathSegmentType.KEY:
                assert isinstance(segment.value, str)
                result = _traverse_key(item, segment.value, strict)
                if isinstance(item, list) and isinstance(result, list):
                    fanned_out = True
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
                    fanned_out = True
                    next_items.extend(result)
                else:
                    next_items.append(result)

            elif segment.type == PathSegmentType.TUPLE:
                assert isinstance(segment.value, list)
                result = _traverse_tuple(item, segment.value, strict)
                next_items.append(result)

        current = next_items

    if fanned_out:
        return [None if item is MISSING else item for item in current]
    return current[0]


def _traverse_key(data: Any, key: str, strict: bool) -> Any:
    """Traverse a key in dict or list of dicts."""
    if isinstance(data, dict):
        if key in data:
            return data[key]
        elif strict:
            raise KeyError(f"Key '{key}' not found")
        else:
            return MISSING

    elif isinstance(data, list):
        results = []
        for item in data:
            if isinstance(item, dict):
                if key in item:
                    results.append(item[key])
                elif strict:
                    raise KeyError(f"Key '{key}' not found in list element")
                else:
                    results.append(MISSING)
            elif strict:
                raise TypeError("Expected dict in list but got different type")
            else:
                results.append(MISSING)
        return results

    elif strict:
        raise TypeError("Expected dict but got different type")
    else:
        return MISSING


def _traverse_index(data: Any, idx: int, strict: bool) -> Any:
    """Traverse an index in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return MISSING

    length = len(data)
    actual_idx = idx if idx >= 0 else length + idx

    if 0 <= actual_idx < length:
        return data[actual_idx]
    elif strict:
        raise IndexError(f"Index {idx} out of range")
    else:
        return MISSING


def _traverse_slice(data: Any, start: int | None, end: int | None, strict: bool) -> Any:
    """Traverse a slice in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return MISSING
    return data[start:end]


def _traverse_wildcard(data: Any, strict: bool) -> Any:
    """Traverse all elements in a list."""
    if not isinstance(data, list):
        if strict:
            raise TypeError("Expected list but got different type")
        return MISSING
    return data


def _traverse_tuple(data: Any, paths: list[Path], strict: bool) -> tuple:
    """Traverse multiple paths and return as tuple."""
    results = []
    for path in paths:
        result = traverse_path(data, path, strict=strict)
        results.append(None if result is MISSING else result)
    return tuple(results)


def apply_functions(
    value: Any, functions: Callable | list[Callable], strict: bool = False
) -> Any:
    """
    Apply a function or list of functions to a value.

    In non-strict mode, a function that raises yields None.
    In strict mode, the exception propagates.
    """
    if not isinstance(functions, list):
        functions = [functions]

    current = value
    for func in functions:
        try:
            current = func(current)
        except Exception:
            if strict:
                raise
            return None

    return current
