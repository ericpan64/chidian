from typing import Any, Callable, Iterable, Union

from . import chidian  # The compiled Rust module

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
    return chidian.get(
        source=source,
        key=key,
        default=default,
        apply=apply,
        only_if=only_if,
        _drop_level=drop_level,
        flatten=flatten,
        strict=strict
    )