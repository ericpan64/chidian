"""
Processing utilities for chidian output transformation.

Combines DROP handling, KEEP unwrapping, and empty value removal.
"""

from typing import Any

from .drop import DROP, _DropSignal
from .keep import KEEP


def is_empty(value: Any) -> bool:
    """Check if a value is considered empty."""
    if value is None:
        return True
    if isinstance(value, dict) and len(value) == 0:
        return True
    if isinstance(value, list) and len(value) == 0:
        return True
    if isinstance(value, str) and len(value) == 0:
        return True
    return False


def process_output(data: Any, remove_empty: bool = True) -> Any:
    """
    Process output data: handle DROPs, unwrap KEEPs, optionally remove empties.

    Args:
        data: The data structure to process
        remove_empty: If True (default), remove empty values ({}, [], "", None)
                     KEEP-wrapped values are preserved regardless of this setting.

    Returns:
        Processed data with DROPs applied, KEEPs unwrapped, and empties removed.
    """
    try:
        return _process_value(data, remove_empty)
    except _DropSignal as signal:
        if signal.levels > 0:
            raise ValueError(
                f"DROP level exceeds structure depth (levels remaining: {signal.levels})"
            )
        # Top-level container was dropped
        if isinstance(data, dict):
            return {}
        elif isinstance(data, list):
            return []
        else:
            return None


def _process_value(data: Any, remove_empty: bool) -> Any:
    """Internal processor that may raise _DropSignal."""
    # Handle DROP sentinel
    if isinstance(data, DROP):
        raise _DropSignal(data.value)

    # Handle KEEP wrapper - process inner value for DROPs but preserve from empty removal
    if isinstance(data, KEEP):
        # Process the inner value to handle any DROP sentinels, but skip empty removal
        return _process_value(data.value, remove_empty=False)

    # Process containers recursively
    if isinstance(data, dict):
        return _process_dict(data, remove_empty)

    if isinstance(data, list):
        return _process_list(data, remove_empty)

    # For scalar values, check if empty and should be removed
    if remove_empty and is_empty(data):
        return None  # Will be filtered out by parent

    return data


def _process_dict(d: dict, remove_empty: bool) -> dict:
    """Process a dict, handling DROP/KEEP and optionally removing empties."""
    result = {}

    for key, value in d.items():
        # Handle KEEP specially - process inner value for DROPs but preserve from empty removal
        if isinstance(value, KEEP):
            try:
                result[key] = _process_value(value.value, remove_empty=False)
            except _DropSignal as signal:
                if signal.levels == 0:
                    pass  # Remove this key
                elif signal.levels == 1:
                    raise _DropSignal(0)
                else:
                    raise _DropSignal(signal.levels - 1)
            continue

        try:
            processed = _process_value(value, remove_empty)

            # Skip empty values if remove_empty is True
            if remove_empty and is_empty(processed):
                continue

            result[key] = processed

        except _DropSignal as signal:
            if signal.levels == 0:
                # Remove this key (don't add to result)
                pass
            elif signal.levels == 1:
                # Remove this dict from its parent
                raise _DropSignal(0)
            else:
                # Propagate further up
                raise _DropSignal(signal.levels - 1)

    return result


def _process_list(lst: list, remove_empty: bool) -> list:
    """Process a list, handling DROP/KEEP and optionally removing empties."""
    result = []

    for item in lst:
        # Handle KEEP specially - process inner value for DROPs but preserve from empty removal
        if isinstance(item, KEEP):
            try:
                result.append(_process_value(item.value, remove_empty=False))
            except _DropSignal as signal:
                if signal.levels == 0:
                    pass  # Remove this item
                elif signal.levels == 1:
                    raise _DropSignal(0)
                else:
                    raise _DropSignal(signal.levels - 1)
            continue

        # Special case: DROP directly in list
        if isinstance(item, DROP):
            if item == DROP.THIS_OBJECT:
                # Just skip this item
                continue
            elif item == DROP.PARENT:
                # Remove this list's parent container
                raise _DropSignal(1)
            else:
                # GRANDPARENT or higher - propagate up
                raise _DropSignal(item.value - 1)

        try:
            processed = _process_value(item, remove_empty)

            # Skip empty values if remove_empty is True
            if remove_empty and is_empty(processed):
                continue

            result.append(processed)

        except _DropSignal as signal:
            if signal.levels == 0:
                # Remove this item (don't add to result)
                pass
            elif signal.levels == 1:
                # Remove this list from its parent
                raise _DropSignal(0)
            else:
                # Propagate further up
                raise _DropSignal(signal.levels - 1)

    return result
