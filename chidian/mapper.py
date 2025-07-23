from enum import Enum
from typing import Any, Callable

"""
A `Mapper` class for independent dict-to-dict transformations.

The Mapper class performs pure data transformations without schema validation.
It takes a dictionary mapping where keys are target fields and values are
transformations to apply to the source data.

Also contains special types for transformation control (DROP, KEEP).
"""


class Mapper:
    def __init__(self, mapping: dict[str, Callable[[dict], Any] | Any]):
        """
        Initialize a Mapper for dict-to-dict transformations.

        Args:
            mapping: A dictionary mapping where:
                    - Keys are target field names
                    - Values can be:
                        - Callable transformations (e.g., lambda, partials, p.get)
                        - Direct values (strings, numbers, etc.)
        """
        if not isinstance(mapping, dict):
            raise TypeError(f"Mapping must be dict, got {type(mapping).__name__}")

        self.mapping = mapping

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply the transformation to input data."""
        result = {}

        for target_field, mapping_spec in self.mapping.items():
            if callable(mapping_spec):
                # Callable mapping (lambda, partial, etc.)
                result[target_field] = mapping_spec(data)
            else:
                # Direct value (including strings)
                result[target_field] = mapping_spec

        return result


class DROP(Enum):
    """
    A DROP placeholder object indicates the object relative to the current value should be dropped.
    An "object" in this context is a dict or a list.

    This enum implements the transformation protocol without inheritance to avoid metaclass conflicts.

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

    def process(self, _data: Any, _context: dict[str, Any] | None = None) -> "DROP":
        """DROP sentinels are processed by Mapper, not directly."""
        return self

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

    def process(self, _data: Any, _context: dict[str, Any] | None = None) -> Any:
        """KEEP sentinels preserve their value during processing."""
        return self.value
