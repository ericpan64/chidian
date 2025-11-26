"""
KEEP wrapper to preserve empty values from automatic removal.
"""

from typing import Any


class KEEP:
    """
    Wrapper to preserve empty values that would otherwise be removed.

    By default, empty values ({}, [], "", None) are removed during processing.
    Wrap with KEEP() to explicitly preserve them.

    Examples:
        KEEP({})      # Preserved as {}
        KEEP(None)    # Preserved as None
        KEEP([])      # Preserved as []
        KEEP("")      # Preserved as ""
    """

    def __init__(self, value: Any):
        self.value = value

    def __repr__(self) -> str:
        return f"KEEP({self.value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, KEEP):
            return self.value == other.value
        return False
