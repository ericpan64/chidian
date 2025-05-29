"""
A SpecialEnumlikeExtraDefinition (abbrv. SEED) is a series of helpful classes/enums that can be used with a `Piper` to modify data.
"""


from collections.abc import Callable
from enum import Enum
from typing import Any, TypeAlias

ApplyFunc: TypeAlias = Callable[[Any], Any]
ConditionalCheck: TypeAlias = Callable[[Any], bool]
MappingFunc: TypeAlias = Callable[..., dict[str, Any]]


class DROP(Enum):
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


class KEEP:
    """
    A value wrapped in a KEEP object should be ignored by the Mapper class when removing values.

    Partial keeping is _not_ supported (i.e. a KEEP object within an object to be DROP-ed).
    """

    def __init__(self, v: Any):
        self.value = v

class ELIF:
    """
    An ELIF object contains a conditional statement and a dictionary which outlines the possible outcomes
    """
    ...

"Coalesce -- grab first one"
class COALESCE:
    def __init__(self, get_func: Callable, paths: list[str], default: Any = None):
        self.get_func = get_func
        self.paths = paths
        self.default = default
    
    def __call__(self, data: Any) -> Any:
        for path in self.paths:
            value = self.get_func(data, path)
            if value is not None and value != "":
                return value
        return self.default

"Split -- make more nested"
class SPLIT:
    def __init__(self, get_func: Callable, path: str, pattern: str, part: int, then: Callable[[Any], Any] = None):
        self.get_func = get_func
        self.path = path
        self.pattern = pattern
        self.part = part
        self.then = then
    
    def __call__(self, data: Any) -> Any:
        value = self.get_func(data, self.path)
        if value is None:
            return None
        parts = value.split(self.pattern)
        if abs(self.part) > len(parts):
            return None
        result = parts[self.part]
        if self.then:
            return self.then(result)
        return result

"Merge -- make less nested, follow merge template"
class MERGE:
    def __init__(self, get_func: Callable, *paths: str, template: str, skip_none: bool = False):
        self.get_func = get_func
        self.paths = paths
        self.template = template
        self.skip_none = skip_none
    
    def __call__(self, data: Any) -> Any:
        values = []
        for path in self.paths:
            value = self.get_func(data, path)
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

"Flat -- make less nested, flatten everything"
class FLATTEN:
    def __init__(self, get_func: Callable, paths: list[str], delimiter: str = ", "):
        self.get_func = get_func
        self.paths = paths
        self.delimiter = delimiter
    
    def __call__(self, data: Any) -> Any:
        all_values = []
        for path in self.paths:
            values = self.get_func(data, path)
            if isinstance(values, list):
                all_values.extend(str(v) for v in values if v is not None)
            elif values is not None:
                all_values.append(str(values))
        return self.delimiter.join(all_values)

"Default value if multiple options available"
class DEFAULT:
    ...