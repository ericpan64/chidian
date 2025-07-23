"""
DataMapping class for pure semantic transformation definitions.
"""

from typing import Any, Callable, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)


class DataMapping:
    """
    Pure semantic transformation definition.
    Only defines WHAT to transform, not HOW to execute it.
    """

    def __init__(
        self,
        transformations: Dict[str, Callable[[dict], Any] | Any],
        input_schema: Optional[Type[BaseModel]] = None,
        output_schema: Optional[Type[BaseModel]] = None,
    ):
        """
        Initialize a semantic data mapping.

        Args:
            transformations: Dict mapping output fields to transformations
            input_schema: Optional Pydantic model for input validation
            output_schema: Optional Pydantic model for output validation
        """
        if not isinstance(transformations, dict):
            raise TypeError(
                f"Transformations must be dict, got {type(transformations).__name__}"
            )

        self.transformations = transformations
        self.input_schema = input_schema
        self.output_schema = output_schema

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
        """Check if this mapping has any schemas defined."""
        return self.input_schema is not None or self.output_schema is not None
