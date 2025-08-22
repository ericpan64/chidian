from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    List,
    Optional,
    TypeVar,
    Union,
)

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from .data_mapping import DataMapping

"""
Mapper class - execution engine for DataMapping with validation strategies.

The Mapper class takes a DataMapping and executes it with different validation modes:
- STRICT: Validate and throw errors
- FLEXIBLE: Validate but continue on errors, collecting issues
- AUTO: Use strict if schemas present, flexible otherwise

Also contains special types for transformation control (DROP, KEEP).
"""

# Define generic type variable for output models
_OutT = TypeVar("_OutT", bound=BaseModel)


class ValidationMode(Enum):
    """Validation modes for mapper execution."""

    STRICT = "strict"  # Validate and throw errors
    FLEXIBLE = "flexible"  # Validate but continue on errors
    AUTO = "auto"  # Strict if schemas present, flexible otherwise


@dataclass
class ValidationIssue:
    """Represents a validation issue in flexible mode."""

    stage: str  # "input" or "output"
    field: Optional[str]
    error: str
    value: Any


class MapperResult(Generic[_OutT]):
    """Result of a mapping operation, potentially with validation issues."""

    def __init__(
        self,
        data: _OutT | dict[str, Any] | Any,
        issues: Optional[List[ValidationIssue]] = None,
    ):
        self.data: _OutT | dict[str, Any] | Any = data
        self.issues = issues or []

    @property
    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def raise_if_issues(self):
        """Raise an exception if there are validation issues."""
        if self.has_issues:
            messages = [f"{i.stage}: {i.error}" for i in self.issues]
            raise ValidationError(f"Validation issues: {'; '.join(messages)}")


class Mapper(Generic[_OutT]):
    """
    Execution engine for DataMapping with validation strategies.
    """

    def __init__(
        self,
        data_mapping_or_dict: Union[
            "DataMapping[_OutT]", dict[str, Any]
        ],  # DataMapping or dict for backward compatibility
        mode: ValidationMode = ValidationMode.AUTO,
        collect_all_errors: bool = True,
    ):
        """
        Initialize a Mapper with a DataMapping and execution mode.

        Args:
            data_mapping_or_dict: DataMapping instance or dict for backward compatibility
            mode: Validation mode (strict, flexible, or auto)
            collect_all_errors: In flexible mode, whether to collect all errors
        """
        # Import here to avoid circular dependency
        from .data_mapping import DataMapping

        # Backward compatibility: if dict is passed, create a DataMapping
        if isinstance(data_mapping_or_dict, dict):
            self.data_mapping: DataMapping[Any] = DataMapping(
                transformations=data_mapping_or_dict
            )
            self._backward_compat = True
        elif isinstance(data_mapping_or_dict, DataMapping):
            self.data_mapping = data_mapping_or_dict
            self._backward_compat = False
        else:
            raise TypeError(
                f"Expected DataMapping or dict, got {type(data_mapping_or_dict).__name__}"
            )

        self.collect_all_errors = collect_all_errors

        # Determine actual mode
        if mode == ValidationMode.AUTO:
            self.mode = (
                ValidationMode.STRICT
                if self.data_mapping.has_schemas
                else ValidationMode.FLEXIBLE
            )
        else:
            self.mode = mode

    def __call__(self, data: Any) -> _OutT | MapperResult[_OutT] | Any:
        """
        Execute the mapping with the configured validation mode.

        Returns:
            - In strict mode: The transformed data (raises on validation errors)
            - In flexible mode: MapperResult with data and any validation issues
            - In backward compat mode with dict: Always returns dict
        """
        # Backward compatibility mode - always return dict
        if self._backward_compat and not self.data_mapping.has_schemas:
            return self.data_mapping.transform(data)

        if self.mode == ValidationMode.STRICT:
            return self._execute_strict(data)
        else:
            return self._execute_flexible(data)

    def _execute_strict(self, data: Any) -> Any:
        """Execute with strict validation - raise on any errors."""
        # Import helpers here to avoid circular dependency
        from .lib.data_mapping_helpers import to_dict, validate_output

        # Convert input to dict if needed (no validation)
        input_dict = to_dict(data) if hasattr(data, "model_dump") else data

        # Apply transformation
        output_dict = self.data_mapping.transform(input_dict)

        # Validate output if schema provided
        if self.data_mapping.output_schema:
            return validate_output(output_dict, self.data_mapping.output_schema)
        return output_dict

    def _execute_flexible(self, data: Any) -> MapperResult:
        """Execute with flexible validation - collect errors but continue."""
        # Import helpers here to avoid circular dependency
        from .lib.data_mapping_helpers import to_dict, validate_output

        issues = []

        # Convert input to dict if needed (no validation)
        input_dict = to_dict(data) if hasattr(data, "model_dump") else data

        # Apply transformation (might fail if input validation failed)
        try:
            output_dict = self.data_mapping.transform(input_dict)
        except Exception as e:
            # If transformation fails, return with error
            issues.append(
                ValidationIssue(
                    stage="transform", field=None, error=str(e), value=input_dict
                )
            )
            return MapperResult(None, issues)

        # Try to validate output
        final_output: Any = output_dict
        if self.data_mapping.output_schema:
            try:
                final_output = validate_output(
                    output_dict, self.data_mapping.output_schema
                )
            except ValidationError as e:
                # Collect output validation errors
                for error in e.errors():
                    issues.append(
                        ValidationIssue(
                            stage="output",
                            field=".".join(str(loc) for loc in error["loc"]),
                            error=error["msg"],
                            value=error.get("input"),
                        )
                    )
                # Return raw output dict if validation fails
                final_output = output_dict

        return MapperResult(final_output, issues)


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
