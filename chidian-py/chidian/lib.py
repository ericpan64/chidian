from typing import Any, Union
import re
from copy import deepcopy


def put(target: Union[dict[str, Any], None], path: str, value: Any, strict: bool = False) -> dict[str, Any]:
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
    # Create a deep copy to avoid mutating the original
    if target is None:
        result = {}
    elif isinstance(target, dict):
        result = deepcopy(target)
    else:
        # We only support dict at root level
        if strict:
            raise ValueError(f"Target must be a dict, got {type(target).__name__}")
        else:
            return {}
    
    # Parse the path into segments
    segments = _parse_put_path(path)
    
    # Check if path starts with index - we don't support arrays at root
    if segments and segments[0]["type"] == "index":
        if strict:
            raise ValueError("Cannot create array at root level - path must start with a key")
        else:
            return result  # Return unchanged
    
    # Navigate to the target location, creating structure as needed
    current = result
    
    for i, segment in enumerate(segments[:-1]):
        if segment["type"] == "key":
            key = segment["value"]
            
            # Ensure current is a dict
            if not isinstance(current, dict):
                if strict:
                    raise ValueError(f"Cannot traverse into non-dict at '{key}'")
                else:
                    # Skip this path
                    return target
            
            # Create the key if it doesn't exist
            if key not in current:
                # Look ahead to see what type we need
                next_segment = segments[i + 1]
                if next_segment["type"] == "index":
                    current[key] = []
                else:
                    current[key] = {}
            elif not isinstance(current[key], (dict, list)):
                # Value exists but is not a container we can traverse into
                if strict:
                    raise ValueError(f"Cannot traverse into non-dict at '{key}'")
                else:
                    return target
            
            current = current[key]
            
        elif segment["type"] == "index":
            idx = segment["value"]
            
            # Ensure current is a list
            if not isinstance(current, list):
                if strict:
                    raise ValueError(f"Cannot index into non-list")
                else:
                    return target
            
            # Expand list if necessary
            if idx >= 0:
                while len(current) <= idx:
                    current.append(None)
            else:
                # Negative indexing only works on existing items
                actual_idx = len(current) + idx
                if actual_idx < 0:
                    if strict:
                        raise ValueError(f"Index {idx} out of range")
                    else:
                        return target
                idx = actual_idx
            
            # Create dict/list at this index if needed
            if current[idx] is None:
                # Look ahead to see what type we need
                if i + 1 < len(segments) - 1:
                    next_segment = segments[i + 1]
                    if next_segment["type"] == "index":
                        current[idx] = []
                    else:
                        current[idx] = {}
                else:
                    # This is the penultimate segment
                    # Look at the final segment to determine type
                    final_segment = segments[-1]
                    if final_segment["type"] == "index":
                        current[idx] = []
                    else:
                        current[idx] = {}
            elif not isinstance(current[idx], (dict, list)):
                # There's a non-dict/non-list value here
                if i + 1 < len(segments):
                    # We need to traverse further but can't
                    if strict:
                        next_seg = segments[i + 1]
                        if next_seg["type"] == "key":
                            raise ValueError(f"Cannot traverse into non-dict at index {idx}")
                        else:
                            raise ValueError(f"Cannot traverse into non-list at index {idx}")
                    else:
                        return target
            
            current = current[idx]
    
    # Set the value at the final segment
    final_segment = segments[-1]
    
    if final_segment["type"] == "key":
        key = final_segment["value"]
        if not isinstance(current, dict):
            if strict:
                raise ValueError(f"Cannot set key '{key}' on non-dict")
            else:
                return target
        current[key] = value
        
    elif final_segment["type"] == "index":
        idx = final_segment["value"]
        if not isinstance(current, list):
            if strict:
                raise ValueError(f"Cannot set index {idx} on non-list")
            else:
                return target
        
        # Expand list if necessary
        if idx >= 0:
            while len(current) <= idx:
                current.append(None)
        else:
            # Negative indexing
            actual_idx = len(current) + idx
            if actual_idx < 0:
                if strict:
                    raise ValueError(f"Index {idx} out of range")
                else:
                    return target
            idx = actual_idx
        
        current[idx] = value
    
    return result


def _parse_put_path(path: str) -> list[dict[str, Union[str, int]]]:
    """
    Parse a path string into segments for the put operation.
    
    Returns a list of dicts with 'type' and 'value' keys.
    Type can be 'key' or 'index'.
    """
    segments = []
    remaining = path
    
    while remaining:
        # Try to match a key at the start
        key_match = re.match(r'^([a-zA-Z_][\w-]*)', remaining)
        if key_match:
            key = key_match.group(1)
            segments.append({"type": "key", "value": key})
            remaining = remaining[len(key):]
            
            # Check for any following brackets
            while remaining and remaining[0] == '[':
                bracket_match = re.match(r'^\[(-?\d+)\]', remaining)
                if bracket_match:
                    idx = int(bracket_match.group(1))
                    segments.append({"type": "index", "value": idx})
                    remaining = remaining[bracket_match.end():]
                else:
                    break
        
        # Try to match a bracket at the start (for paths starting with [)
        elif remaining and remaining[0] == '[':
            bracket_match = re.match(r'^\[(-?\d+)\]', remaining)
            if bracket_match:
                idx = int(bracket_match.group(1))
                segments.append({"type": "index", "value": idx})
                remaining = remaining[bracket_match.end():]
            else:
                raise ValueError(f"Invalid bracket syntax in path: '{path}'")
        
        # Skip dots
        if remaining and remaining[0] == '.':
            remaining = remaining[1:]
        elif remaining:
            # We have remaining content but can't parse it
            raise ValueError(f"Invalid path syntax at: '{remaining}' in path: '{path}'")
    
    if not segments:
        raise ValueError(f"Invalid path: '{path}'")
    
    return segments