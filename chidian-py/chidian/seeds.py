"""
A SpecialEnumlikeExtraDefinition (abbrv. SEED) is a series of helpful classes/enums that can be used with a `Piper` to modify data.
"""


from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeAlias

from .chidian_rs import get

ApplyFunc: TypeAlias = Callable[[Any], Any]
ConditionalCheck: TypeAlias = Callable[[Any], bool]
MappingFunc: TypeAlias = Callable[..., dict[str, Any]]


class SEED(ABC):
    """Base class for all SEED objects.
    
    SEEDs are special objects that modify data processing behavior in DictPiper.
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
    
    # Class-level constants for common drop levels
    THIS_OBJECT = DropLevel.THIS_OBJECT
    PARENT = DropLevel.PARENT
    GRANDPARENT = DropLevel.GRANDPARENT
    GREATGRANDPARENT = DropLevel.GREATGRANDPARENT
    
    def __init__(self, level: DropLevel):
        self.level = level
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        """DROP seeds are processed by DictPiper, not directly."""
        return self
    
    @classmethod
    def this_object(cls) -> 'DROP':
        return cls(DropLevel.THIS_OBJECT)
    
    @classmethod
    def parent(cls) -> 'DROP':
        return cls(DropLevel.PARENT)
    
    @classmethod
    def grandparent(cls) -> 'DROP':
        return cls(DropLevel.GRANDPARENT)
    
    @classmethod
    def greatgrandparent(cls) -> 'DROP':
        return cls(DropLevel.GREATGRANDPARENT)


# Create module-level constants for backward compatibility
DROP.THIS_OBJECT = DROP.this_object()
DROP.PARENT = DROP.parent()
DROP.GRANDPARENT = DROP.grandparent()
DROP.GREATGRANDPARENT = DROP.greatgrandparent()


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

class CASE(SEED):
    """Switch-like pattern matching for values with ordered evaluation."""
    
    def __init__(self, path: str, cases: dict[Any, Any] | list[tuple[Any, Any]], default: Any = None):
        self.path = path
        # Support both dict and list for ordered evaluation
        if isinstance(cases, dict):
            self.cases = list(cases.items())
        else:
            self.cases = cases
        self.default = default
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        value = get(data, self.path)
        
        for case_key, case_value in self.cases:
            # Exact match
            if not callable(case_key) and value == case_key:
                return case_value
            
            # Function match
            if callable(case_key):
                try:
                    if case_key(value):
                        return case_value
                except (TypeError, AttributeError):
                    continue
        
        return self.default
    
    def __call__(self, data: Any) -> Any:
        """Allow callable syntax for backward compatibility."""
        return self.process(data)

class COALESCE(SEED):
    """Coalesce -- grab first non-empty value from multiple paths."""
    
    def __init__(self, paths: list[str], default: Any = None):
        self.paths = paths
        self.default = default
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        for path in self.paths:
            value = get(data, path)
            if value is not None and value != "":
                return value
        return self.default
    
    def __call__(self, data: Any) -> Any:
        """Allow callable syntax for backward compatibility."""
        return self.process(data)

class SPLIT(SEED):
    """Split -- extract part of a string by splitting on a pattern."""
    
    def __init__(self, path: str, pattern: str, part: int, then: Callable[[Any], Any] = None):
        self.path = path
        self.pattern = pattern
        self.part = part
        self.then = then
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        value = get(data, self.path)
        if value is None:
            return None
        parts = value.split(self.pattern)
        # Check bounds: for positive indices, must be < len(parts)
        # for negative indices, must be >= -len(parts)
        if self.part >= len(parts) or self.part < -len(parts):
            return None
        result = parts[self.part]
        if self.then:
            return self.then(result)
        return result
    
    def __call__(self, data: Any) -> Any:
        """Allow callable syntax for backward compatibility."""
        return self.process(data)

class MERGE(SEED):
    """Merge -- combine multiple values using a template."""
    
    def __init__(self, *paths: str, template: str, skip_none: bool = False):
        self.paths = paths
        self.template = template
        self.skip_none = skip_none
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        values = []
        for path in self.paths:
            value = get(data, path)
            if self.skip_none:
                if value is not None:
                    values.append(value)
            else:
                values.append(value)
        
        if self.skip_none:
            # When skip_none is True, we need to adjust the template
            # Count the number of placeholders in template
            import re
            placeholders = len(re.findall(r'\{\}', self.template))
            # Create a new template with the right number of placeholders
            if len(values) < placeholders:
                parts = self.template.split('{}')
                new_template = ''
                for i, part in enumerate(parts[:-1]):
                    if i < len(values):
                        new_template += part + '{}'
                    else:
                        # Skip the separator between missing values
                        if i == len(values) and part.endswith(' '):
                            new_template += part.rstrip()
                new_template += parts[-1]
                # Adjust template to match actual values
                new_template = ' '.join('{}' for _ in values)
                return new_template.format(*values)
        
        return self.template.format(*values)
    
    def __call__(self, data: Any) -> Any:
        """Allow callable syntax for backward compatibility."""
        return self.process(data)

class FLATTEN(SEED):
    """Flatten -- combine multiple values or lists into a single delimited string."""
    
    def __init__(self, paths: list[str], delimiter: str = ", "):
        self.paths = paths
        self.delimiter = delimiter
    
    def process(self, data: Any, context: dict[str, Any] | None = None) -> Any:
        all_values = []
        for path in self.paths:
            values = get(data, path)
            if isinstance(values, list):
                all_values.extend(str(v) for v in values if v is not None)
            elif values is not None:
                all_values.append(str(values))
        return self.delimiter.join(all_values)
    
    def __call__(self, data: Any) -> Any:
        """Allow callable syntax for backward compatibility."""
        return self.process(data)
