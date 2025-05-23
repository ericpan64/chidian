from typing import Any, Callable, Iterable, Union
import re

# Type aliases for clarity
ApplyFunc = Callable[[Any], Any]
ConditionalCheck = Callable[[Any], bool]
DROP = str  # Placeholder for now

def get(
    source: Union[dict[str, Any], list[Any]],
    key: str,
    default: Any = None,
    apply: Union[ApplyFunc, Iterable[ApplyFunc], None] = None,
    only_if: Union[ConditionalCheck, None] = None,
    drop_level: Union[DROP, None] = None,
    flatten: bool = False,
    strict: Union[bool, None] = None,
) -> Any: 
    """
    Extract values from nested data structures using a key path.
    
    Supports:
    - Dot notation: "data.patient.id"
    - Array indexing: "list_data[0].patient", "list_data[-1].patient"
    - Array slicing: "list_data[1:3]", "list_data[1:]", "list_data[:2]"
    - Wildcard expansion: "[*].patient", "data[*].patient.active"
    - Tuple extraction: "data.patient.(id,active)"
    - Apply functions for transformation
    - Conditional extraction with only_if
    - Flattening nested arrays
    - Strict mode for error handling
    
    Args:
        source: The data structure to extract from
        key: The path expression
        default: Value to return if key is not found
        apply: Function or list of functions to apply to result
        only_if: Conditional check function
        drop_level: Not implemented yet
        flatten: Whether to flatten nested arrays
        strict: Whether to raise errors on missing keys (None = use mapping context)
        
    Returns:
        The extracted value, possibly transformed
    """
    # Determine effective strict mode
    effective_strict = strict
    if effective_strict is None:
        # Import here to avoid circular imports
        try:
            from .dicts.mapper import is_strict_mode
            effective_strict = is_strict_mode()
        except ImportError:
            effective_strict = False
    
    try:
        result = _get_value(source, key, default)
        
        # Apply only_if check first
        if only_if is not None:
            if not only_if(result):
                return None
        
        # Apply transformation functions
        if apply is not None:
            result = _apply_functions(result, apply)
            
        # Apply flattening if requested
        if flatten and isinstance(result, list):
            result = _flatten_list(result)
            
        return result
        
    except (KeyError, IndexError, ValueError, TypeError, AttributeError) as e:
        if effective_strict:
            raise ValueError(f"Key '{key}' not found in source") from e
        return default


def _get_value(source: Any, key: str, default: Any = None) -> Any:
    """Extract value using the key path."""
    
    # Handle tuple extraction: "field.(a,b,c)"
    if '(' in key and ')' in key:
        return _handle_tuple_extraction(source, key, default)
    
    # Handle array wildcard or slicing operations
    if '[' in key:
        return _handle_array_operations(source, key)
    
    # Simple dot notation
    if '.' in key:
        return _handle_dot_notation(source, key)
    
    # Single key
    if isinstance(source, dict):
        return source[key]
    else:
        raise KeyError(f"Cannot access key '{key}' on non-dict")


def _handle_tuple_extraction(source: Any, key: str, default: Any = None) -> Any:
    """Handle tuple extraction like 'data.patient.(id,active)'."""
    # Find the tuple part - don't capture the dot before the parentheses
    match = re.search(r'(.+?)\.?\(([^)]+)\)', key)
    if not match:
        raise ValueError(f"Invalid tuple syntax in key: {key}")
    
    prefix = match.group(1)
    tuple_keys = [k.strip() for k in match.group(2).split(',')]
    
    # Get the base object
    if prefix:
        base_obj = _get_value(source, prefix)
    else:
        base_obj = source
    
    # Handle arrays - apply tuple extraction to each element
    if isinstance(base_obj, list):
        return _apply_tuple_to_list(base_obj, tuple_keys, default)
    else:
        return _extract_tuple_from_object(base_obj, tuple_keys, default)


def _apply_tuple_to_list(lst: list, tuple_keys: list[str], default: Any = None) -> list:
    """Apply tuple extraction to a list, handling nested lists recursively."""
    result = []
    for item in lst:
        if isinstance(item, list):
            # Nested list - apply recursively
            result.append(_apply_tuple_to_list(item, tuple_keys, default))
        else:
            # Single object - extract tuple
            result.append(_extract_tuple_from_object(item, tuple_keys, default))
    return result


def _extract_tuple_from_object(obj: Any, keys: list[str], default: Any = None) -> tuple:
    """Extract multiple keys from an object as a tuple."""
    result = []
    for key in keys:
        try:
            value = _get_value(obj, key)
            result.append(value)
        except (KeyError, IndexError, ValueError, TypeError):
            result.append(default)
    return tuple(result)


def _handle_array_operations(source: Any, key: str) -> Any:
    """Handle array operations like indexing, slicing, and wildcards."""
    
    # Parse the key to find array operations
    parts = []
    current_part = ""
    bracket_depth = 0
    
    for char in key:
        if char == '[':
            if current_part:
                parts.append(current_part)
                current_part = ""
            bracket_depth += 1
            current_part += char
        elif char == ']':
            current_part += char
            bracket_depth -= 1
            if bracket_depth == 0:
                parts.append(current_part)
                current_part = ""
        elif char == '.' and bracket_depth == 0:
            if current_part:
                parts.append(current_part)
                current_part = ""
        else:
            current_part += char
    
    if current_part:
        parts.append(current_part)
    
    # Process parts sequentially
    current_value = source
    for part in parts:
        if part.startswith('[') and part.endswith(']'):
            # Array operation
            current_value = _apply_array_operation(current_value, part)
        else:
            # Field access
            current_value = _apply_field_access(current_value, part)
    
    return current_value


def _apply_array_operation(value: Any, operation: str) -> Any:
    """Apply array operation like [0], [-1], [1:3], [*]."""
    
    # If we have a list where each element is itself an array,
    # apply the operation to each sub-array
    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], list):
        results = []
        for subarray in value:
            if isinstance(subarray, list):
                results.append(_apply_array_operation(subarray, operation))
            else:
                results.append(None)  # Handle missing/null arrays
        return results
    
    # Standard case: single array
    if not isinstance(value, list):
        raise TypeError(f"Cannot apply array operation {operation} to non-list")
    
    # Remove brackets
    op = operation[1:-1]
    
    # Handle wildcard
    if op == '*':
        return value
    
    # Handle slicing
    if ':' in op:
        parts = op.split(':')
        start = int(parts[0]) if parts[0] else None
        end = int(parts[1]) if parts[1] else None
        return value[start:end]
    
    # Handle single index
    try:
        index = int(op)
        return value[index]
    except (ValueError, IndexError):
        raise IndexError(f"Invalid array index: {op}")


def _apply_field_access(value: Any, field: str) -> Any:
    """Apply field access to value(s)."""
    if isinstance(value, list):
        # Apply field access to each element in the list
        results = []
        for item in value:
            try:
                result = _get_single_field(item, field)
                results.append(result)
            except (TypeError, KeyError):
                results.append(None)
        return results
    else:
        return _get_single_field(value, field)


def _get_single_field(obj: Any, field: str) -> Any:
    """Get a single field from an object."""
    if isinstance(obj, dict):
        return obj.get(field)
    elif isinstance(obj, list):
        # Handle list of objects - apply field access to each
        return [_get_single_field(item, field) for item in obj]
    else:
        raise TypeError(f"Cannot access field '{field}' on {type(obj)}")


def _handle_dot_notation(source: Any, key: str) -> Any:
    """Handle simple dot notation like 'data.patient.id'."""
    keys = key.split('.')
    current = source
    
    for k in keys:
        if isinstance(current, dict):
            current = current[k]
        elif isinstance(current, list):
            current = current[int(k)]
        else:
            raise KeyError(f"Cannot access key '{k}' on {type(current)}")
    
    return current


def _apply_functions(value: Any, apply: Union[ApplyFunc, Iterable[ApplyFunc]]) -> Any:
    """Apply transformation functions to the value."""
    if callable(apply):
        return apply(value)
    elif hasattr(apply, '__iter__'):
        result = value
        for func in apply:
            if result is None:
                return None
            result = func(result)
        return result
    else:
        return value


def _flatten_list(lst: list) -> list:
    """Flatten a nested list, removing None values."""
    result = []
    for item in lst:
        if isinstance(item, list):
            result.extend(_flatten_list(item))
        elif item is not None:
            result.append(item)
    return result