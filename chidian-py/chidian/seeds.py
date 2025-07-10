"""
SEED classes provide data transformation directives for use with Piper.

Contains DROP (enum for indicating data removal) and KEEP (class for preserving values).
All SEED objects implement a process() method for consistent interface.
"""

from enum import Enum
from typing import Any

from chidian_py_rs import SeedDrop, SeedKeep  # type: ignore[attr-defined]


class DROP(Enum):
    """
    A DROP placeholder object indicates the object relative to the current value should be dropped.
    An "object" in this context is a dict or a list.

    This enum implements the SEED protocol without inheritance to avoid metaclass conflicts.

    Examples:
    ```
    {   <-- Grandparent (rel to _value)
        'A': {   <-- Parent (rel to _value)
            'B': {      <-- This Object (rel to _value)
                'C': _value
            }
        }
    }
    ```

    ```
    {   <-- Grandparent (rel to _value1 and _value2)
        'A': [  <-- Parent (rel to _value1 and _value2)
            {       <-- This Object (rel to _value1)
                'B': _value1
            },
            {       <-- This Object (rel to _value2)
                'B': _value2
            }
        ]
    }
    ```
    """

    THIS_OBJECT = -1
    PARENT = -2
    GRANDPARENT = -3
    GREATGRANDPARENT = -4

    def process(self, _data: Any, _context: dict[str, Any] | None = None) -> Any:
        """DROP seeds are processed by Piper, not directly."""
        rust_drop = SeedDrop(self.value)
        return rust_drop.process(_data, _context)

    @property
    def level(self) -> int:
        """Get the drop level value for compatibility."""
        return self.value


class KEEP:
    """
    A value wrapped in a KEEP object should be ignored by the Mapper class when removing values.

    Partial keeping is _not_ supported (i.e. a KEEP object within an object to be DROP-ed).
    """

    def __init__(self, value: Any):
        self.value = value
        self._rust_keep = SeedKeep(value)

    def process(self, _data: Any, _context: dict[str, Any] | None = None) -> Any:
        """KEEP seeds preserve their value during processing."""
        return self._rust_keep.process(_data, _context)
