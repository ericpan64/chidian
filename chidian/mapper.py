from dataclasses import dataclass
from enum import Enum
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
)

from pydantic import BaseModel, ValidationError

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
    Data transformation engine with validation strategies.
    Combines semantic transformation definition with execution logic.
    """

    def __init__(
        self,
        transformations: Mapping[str, Callable[..., Any] | Any],
        output_schema: Optional[Type[_OutT]] = None,
        mode: ValidationMode = ValidationMode.AUTO,
        min_input_schemas: Optional[List[Type[BaseModel]]] = None,
        other_input_schemas: Optional[List[Type[BaseModel]]] = None,
        collect_all_errors: bool = True,
    ):
        """
        Initialize a Mapper with transformations and validation configuration.

        Args:
            transformations: Dict mapping output fields to transformations
            output_schema: Optional Pydantic model for output validation
            mode: Validation mode (strict, flexible, or auto)
            min_input_schemas: Minimal set of source models (metadata-only)
            other_input_schemas: Additional source models (metadata-only)
            collect_all_errors: In flexible mode, whether to collect all errors
        """
        # Convert Mapping to dict if needed
        if isinstance(transformations, dict):
            self.transformations = transformations
        elif hasattr(transformations, "items"):
            # Support Mapping types by converting to dict
            self.transformations = dict(transformations)
        else:
            raise TypeError(
                f"Transformations must be dict or Mapping, got {type(transformations).__name__}"
            )
        self.output_schema = output_schema
        self.min_input_schemas = min_input_schemas or []
        self.other_input_schemas = other_input_schemas or []
        self._backward_compat = False

        self.collect_all_errors = collect_all_errors

        # Determine actual mode
        if mode == ValidationMode.AUTO:
            self.mode = (
                ValidationMode.STRICT if self.has_schemas else ValidationMode.FLEXIBLE
            )
        else:
            self.mode = mode

    def transform(self, data: dict) -> dict:
        """
        Apply the pure transformation logic.
        This is the core semantic transformation without any validation.
        """
        result = {}

        for target_field, transform_spec in self.transformations.items():
            if callable(transform_spec):
                result[target_field] = transform_spec(data)
            else:
                result[target_field] = transform_spec

        return result

    @property
    def has_schemas(self) -> bool:
        """Check if this mapping has output schema defined."""
        return self.output_schema is not None

    def __call__(self, data: Any) -> _OutT | MapperResult[_OutT] | Any:
        """
        Execute the mapping with the configured validation mode.

        Returns:
            - In strict mode: The transformed data (raises on validation errors)
            - In flexible mode: MapperResult with data and any validation issues
            - In backward compat mode with dict: Always returns dict
        """
        # For non-schema mode, just return dict
        if not self.has_schemas and self.mode == ValidationMode.FLEXIBLE:
            return self.transform(data)

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
        output_dict = self.transform(input_dict)

        # Validate output if schema provided
        if self.output_schema:
            return validate_output(output_dict, self.output_schema)
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
            output_dict = self.transform(input_dict)
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
        if self.output_schema:
            try:
                final_output = validate_output(output_dict, self.output_schema)
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
