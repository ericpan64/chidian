"""
DataMapping class for pure semantic transformation definitions.
"""

from typing import Any, Callable, Dict, Generic, List, Optional, Type, TypeVar

from pydantic import BaseModel

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)
_OutT = TypeVar("_OutT", bound=BaseModel)


class DataMapping(Generic[_OutT]):
    """
    Pure semantic transformation definition.
    Only defines WHAT to transform, not HOW to execute it.

    The min_input_schemas and other_input_schemas are metadata-only fields
    that document the expected source models but are not enforced at runtime.
    """

    def __init__(
        self,
        transformations: Dict[str, Callable[[dict], Any] | Any],
        output_schema: Optional[Type[_OutT]] = None,
        min_input_schemas: Optional[List[Type[BaseModel]]] = None,
        other_input_schemas: Optional[List[Type[BaseModel]]] = None,
    ):
        """
        Initialize a semantic data mapping.

        Args:
            transformations: Dict mapping output fields to transformations
            output_schema: Optional Pydantic model for output validation
            min_input_schemas: Minimal set of source models expected to produce
                essential output fields (metadata-only, not enforced)
            other_input_schemas: Additional source models that, together with
                min_input_schemas, comprise the complete set needed to fully
                populate the output_schema (metadata-only, not enforced)
        """
        if not isinstance(transformations, dict):
            raise TypeError(
                f"Transformations must be dict, got {type(transformations).__name__}"
            )

        self.transformations = transformations
        self.output_schema = output_schema
        self.min_input_schemas = min_input_schemas or []
        self.other_input_schemas = other_input_schemas or []

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
