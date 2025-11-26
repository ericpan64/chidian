"""
DROP sentinel for conditional removal of values from output.
"""

from enum import Enum


class DROP(Enum):
    """
    Sentinel indicating a value (or its container) should be dropped from output.

    DROP propagates upward through the structure:
    - THIS_OBJECT: Remove the dict/list containing this DROP value
    - PARENT: Remove the parent of that container
    - GRANDPARENT: Remove two levels up
    - GREATGRANDPARENT: Remove three levels up (raises if out of bounds)

    In lists, DROP.THIS_OBJECT removes just that item (not the whole list).

    Examples:
        # DROP.THIS_OBJECT removes the containing dict
        {"dropped": {"trigger": DROP.THIS_OBJECT, "ignored": "x"}}
        # Result: {}  (the inner dict is removed, so "dropped" has no value)

        # In a list, DROP.THIS_OBJECT removes just that item
        ["first", DROP.THIS_OBJECT, "third"]
        # Result: ["first", "third"]

        # DROP.PARENT removes the parent container
        {"items": [{"bad": DROP.PARENT}, {"good": "value"}]}
        # Result: {}  (the list is removed, so "items" has no value)
    """

    THIS_OBJECT = 1
    PARENT = 2
    GRANDPARENT = 3
    GREATGRANDPARENT = 4


class _DropSignal(Exception):
    """Internal signal for DROP propagation."""

    def __init__(self, levels: int):
        self.levels = levels


def process_drops(data):
    """
    Recursively process a data structure, handling DROP sentinels.

    Returns the processed data with DROPs applied.
    If DROP propagates to the top level, returns {} for dict input or [] for list input.
    """
    try:
        return _process_value(data)
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


def _process_value(data):
    """Internal processor that may raise _DropSignal."""
    if isinstance(data, DROP):
        raise _DropSignal(data.value)

    if isinstance(data, dict):
        return _process_dict(data)

    if isinstance(data, list):
        return _process_list(data)

    return data


def _process_dict(d: dict) -> dict:
    """Process a dict, handling DROP sentinels in values."""
    result = {}

    for key, value in d.items():
        try:
            processed = _process_value(value)
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


def _process_list(lst: list) -> list:
    """Process a list, handling DROP sentinels in items."""
    result = []

    for item in lst:
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
            processed = _process_value(item)
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
