"""
A SpecialEnumlikeExtraDefinition (abbrv. SEED) is a series of helpful classes/enums that can be used with a `Piper` to modify data.
"""


from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeAlias

class SEED(ABC):
    """Base class for all SEED objects.
    
    SEEDs are special objects that modify data processing behavior in Piper.
    They can be consumed during mapping execution to perform transformations,
    conditionals, or structural modifications.
    """
    
    @abstractmethod
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        """Process the seed with given data and optional context.
        
        Args:
            data: The input data to process
            context: Optional context containing parent references, indices, etc.
        
        Returns:
            The processed result
        """
        pass

# TODO: Along with note in `DROP` -- could this be removed and consolidated?
class DropLevel(Enum):
    """
    A DROP placeholder object indicates the object relative to the current value should be dropped. 
      An "object" in this context is a dict or a list.

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


class DROP(SEED):
    """
    A DROP placeholder object indicates the object relative to the current value should be dropped.
    An "object" in this context is a dict or a list.
    """
    
    # TODO: Is there a way to have this be `DROP.THIS_OBJECT` as the object in the code
    #       E.g. originally it was `class DROP(Enum)` so this wasn't an issue, maybe this should be
    #       update to be `class DROP(Enum, SEED)`? Be an enum that implements `process`
    # Class-level constants for common drop levels
    THIS_OBJECT = DropLevel.THIS_OBJECT
    PARENT = DropLevel.PARENT
    GRANDPARENT = DropLevel.GRANDPARENT
    GREATGRANDPARENT = DropLevel.GREATGRANDPARENT
    
    def __init__(self, level: DropLevel):
        self.level = level
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        """DROP seeds are processed by Piper, not directly."""
        return self

class KEEP(SEED):
    """
    A value wrapped in a KEEP object should be ignored by the Mapper class when removing values.

    Partial keeping is _not_ supported (i.e. a KEEP object within an object to be DROP-ed).
    """

    def __init__(self, value: Any):
        self.value = value
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        """KEEP seeds preserve their value during processing."""
        return self.value

