import re
from copy import deepcopy
from typing import Any

try:
    from .chidian_rs import put as rust_put
    from .chidian_rs import should_use_rust_put

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False
    rust_put = None
    should_use_rust_put = None


def put(
    target: dict[str, Any], path: str, value: Any, strict: bool = False
) -> dict[str, Any]:
    """
    Set a value at a specific path in a nested dictionary structure.

    This is the complement to the `get` function, allowing you to set values
    using dot notation paths.

    Args:
        target: The dictionary to modify (will not be mutated)
        path: The path where to set the value (e.g., "patient.name.given")
        value: The value to set at the path
        strict: If True, raise errors when path cannot be created

    Returns:
        A new dictionary with the value set at the specified path

    Examples:
        >>> put({}, "patient.id", "123")
        {'patient': {'id': '123'}}

        >>> put({}, "items[0].value", 42)
        {'items': [{'value': 42}]}

        >>> put({"patient": {"name": "John"}}, "patient.id", "123")
        {'patient': {'name': 'John', 'id': '123'}}
    """
    # Check if we should use the Rust implementation
    if RUST_AVAILABLE and should_use_rust_put and should_use_rust_put():
        return rust_put(target, path, value, strict)

    # Fall back to Python implementation
    return _put_python(target, path, value, strict)


def _put_python(
    target: dict[str, Any], path: str, value: Any, strict: bool = False
) -> dict[str, Any]:
    """Python implementation of put function."""
    # Create a deep copy to avoid mutating the original
    result = deepcopy(target)

    # Parse the path into segments
    segments = _parse_put_path(path)

    # Check if path starts with index - we don't support arrays at root
    if segments and segments[0]["type"] == "index":
        if strict:
            raise ValueError(
                "Cannot create array at root level - path must start with a key"
            )
        else:
            return result  # Return unchanged

    # Navigate to the target location, creating structure as needed
    current = result

    # Navigate to the target location, creating structure as needed
    for i, segment in enumerate(segments[:-1]):
        current = _navigate_path_segment(current, segment, segments, i, target, strict)

    # Set the value at the final segment
    _set_final_value(current, segments[-1], value, strict)

    return result


def _parse_put_path(path: str) -> list[dict[str, str | int]]:
    """
    Parse a path string into segments for the put operation.

    Returns a list of dicts with 'type' and 'value' keys.
    Type can be 'key' or 'index'.
    """
    segments = []
    remaining = path

    while remaining:
        # Try to match a key at the start
        key_match = re.match(r"^([a-zA-Z_][\w-]*)", remaining)
        if key_match:
            key = key_match.group(1)
            segments.append({"type": "key", "value": key})
            remaining = remaining[len(key) :]

            # Check for any following brackets
            while remaining and remaining[0] == "[":
                bracket_match = re.match(r"^\[(-?\d+)\]", remaining)
                if bracket_match:
                    idx = int(bracket_match.group(1))
                    segments.append({"type": "index", "value": idx})
                    remaining = remaining[bracket_match.end() :]
                else:
                    break

        # Try to match a bracket at the start (for paths starting with [)
        elif remaining and remaining[0] == "[":
            bracket_match = re.match(r"^\[(-?\d+)\]", remaining)
            if bracket_match:
                idx = int(bracket_match.group(1))
                segments.append({"type": "index", "value": idx})
                remaining = remaining[bracket_match.end() :]
            else:
                raise ValueError(f"Invalid bracket syntax in path: '{path}'")

        # Skip dots
        if remaining and remaining[0] == ".":
            remaining = remaining[1:]
        elif remaining:
            # We have remaining content but can't parse it
            raise ValueError(f"Invalid path syntax at: '{remaining}' in path: '{path}'")

    if not segments:
        raise ValueError(f"Invalid path: '{path}'")

    return segments


def _navigate_path_segment(
    current: Any,
    segment: dict[str, str | int],
    segments: list[dict[str, str | int]],
    index: int,
    target: dict[str, Any],
    strict: bool,
) -> Any:
    """Navigate through a single path segment, creating containers as needed."""
    if segment["type"] == "key":
        return _navigate_key_segment(current, segment, segments, index, target, strict)
    elif segment["type"] == "index":
        return _navigate_index_segment(
            current, segment, segments, index, target, strict
        )
    else:
        raise ValueError(f"Unknown segment type: {segment['type']}")


def _navigate_key_segment(
    current: Any,
    segment: dict[str, str | int],
    segments: list[dict[str, str | int]],
    index: int,
    target: dict[str, Any],
    strict: bool,
) -> Any:
    """Navigate through a key segment in the path."""
    key = segment["value"]

    # Type guard: key should be str for dict access
    if not isinstance(key, str):
        if strict:
            raise ValueError(f"Dictionary key must be string, got {type(key)}")
        else:
            return target

    # Ensure current is a dict
    if not isinstance(current, dict):
        if strict:
            raise ValueError(f"Cannot traverse into non-dict at '{key}'")
        else:
            return target

    # Create or validate the key
    _ensure_key_exists(current, key, segments, index, strict)

    return current[key]


def _navigate_index_segment(
    current: Any,
    segment: dict[str, str | int],
    segments: list[dict[str, str | int]],
    index: int,
    target: dict[str, Any],
    strict: bool,
) -> Any:
    """Navigate through an index segment in the path."""
    idx = segment["value"]

    # Type guard: idx should be int for list access
    if not isinstance(idx, int):
        if strict:
            raise ValueError(f"List index must be integer, got {type(idx)}")
        else:
            return target

    # Ensure current is a list
    if not isinstance(current, list):
        if strict:
            raise ValueError("Cannot index into non-list")
        else:
            return target

    # Handle list expansion and negative indexing
    expanded_idx = _expand_list_for_index(current, idx, strict)
    if expanded_idx is None:  # Error case in non-strict mode
        return target

    # Create container at index if needed
    _ensure_index_container(current, expanded_idx, segments, index, strict)

    return current[expanded_idx]


def _ensure_key_exists(
    current: dict,
    key: str,
    segments: list[dict[str, str | int]],
    index: int,
    strict: bool,
) -> None:
    """Ensure a key exists in the dictionary with the correct container type."""
    next_segment = segments[index + 1]
    needs_list = next_segment["type"] == "index"

    if key not in current:
        # Create new container of the correct type
        current[key] = [] if needs_list else {}
    elif not isinstance(current[key], (dict, list)):
        # Replace non-container value
        if strict:
            raise ValueError(f"Cannot traverse into non-dict at '{key}'")
        else:
            current[key] = [] if needs_list else {}
    elif isinstance(current[key], dict) and needs_list:
        # Have dict but need list
        if strict:
            raise ValueError(f"Cannot index into dict at '{key}' - expected list")
        else:
            current[key] = []
    elif isinstance(current[key], list) and not needs_list:
        # Have list but need dict
        if strict:
            raise ValueError(f"Cannot access key in list at '{key}' - expected dict")
        else:
            current[key] = {}


def _expand_list_for_index(current: list, idx: int, strict: bool) -> int | None:
    """Expand list if necessary and handle negative indexing."""
    if idx >= 0:
        # Positive index - expand list if needed
        while len(current) <= idx:
            current.append(None)
        return idx
    else:
        # Negative indexing - only works on existing items
        actual_idx = len(current) + idx
        if actual_idx < 0:
            if strict:
                raise ValueError(f"Index {idx} out of range")
            else:
                return None  # Signal error in non-strict mode
        return actual_idx


def _ensure_index_container(
    current: list,
    idx: int,
    segments: list[dict[str, str | int]],
    index: int,
    strict: bool,
) -> None:
    """Ensure the container at the given index has the correct type."""
    if current[idx] is None:
        # Determine what type of container we need
        needs_list = _determine_next_container_type(segments, index)
        current[idx] = [] if needs_list else {}
    elif not isinstance(current[idx], (dict, list)):
        # There's a non-container value here
        if index + 1 < len(segments):
            # We need to traverse further but can't
            if strict:
                next_seg = segments[index + 1]
                if next_seg["type"] == "key":
                    raise ValueError(f"Cannot traverse into non-dict at index {idx}")
                else:
                    raise ValueError(f"Cannot traverse into non-list at index {idx}")


def _determine_next_container_type(
    segments: list[dict[str, str | int]], index: int
) -> bool:
    """Determine if the next container should be a list (True) or dict (False)."""
    if index + 1 < len(segments) - 1:
        # Look at the next segment
        next_segment = segments[index + 1]
        return next_segment["type"] == "index"
    else:
        # This is the penultimate segment - look at the final segment
        final_segment = segments[-1]
        return final_segment["type"] == "index"


def _set_final_value(
    current: Any, final_segment: dict[str, str | int], value: Any, strict: bool
) -> None:
    """Set the value at the final segment of the path."""
    if final_segment["type"] == "key":
        _set_key_value(current, final_segment, value, strict)
    elif final_segment["type"] == "index":
        _set_index_value(current, final_segment, value, strict)


def _set_key_value(
    current: Any, segment: dict[str, str | int], value: Any, strict: bool
) -> None:
    """Set a value at a key in a dictionary."""
    key = segment["value"]

    # Type guard: key should be str for dict access
    if not isinstance(key, str):
        if strict:
            raise ValueError(f"Dictionary key must be string, got {type(key)}")
        else:
            return

    if not isinstance(current, dict):
        if strict:
            raise ValueError(f"Cannot set key '{key}' on non-dict")
        else:
            return

    current[key] = value


def _set_index_value(
    current: Any, segment: dict[str, str | int], value: Any, strict: bool
) -> None:
    """Set a value at an index in a list."""
    idx = segment["value"]

    # Type guard: idx should be int for list access
    if not isinstance(idx, int):
        if strict:
            raise ValueError(f"List index must be integer, got {type(idx)}")
        else:
            return

    if not isinstance(current, list):
        if strict:
            raise ValueError(f"Cannot set index {idx} on non-list")
        else:
            return

    # Handle list expansion and negative indexing
    expanded_idx = _expand_list_for_index(current, idx, strict)
    if expanded_idx is None:  # Error case in non-strict mode
        return

    current[expanded_idx] = value
