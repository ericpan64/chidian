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
