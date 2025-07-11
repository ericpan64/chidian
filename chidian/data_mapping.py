"""
DataMapping class as forward-only validator wrapper around Piper.
"""

from typing import Any, Generic, Type, TypeVar

from pydantic import BaseModel

from .piper import Piper

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)


class DataMapping(Generic[_InModel, _OutModel]):
    """
    A forward-only data mapping with schema validation.

    Takes a Piper for transformation logic and Pydantic schemas for validation.
    Validates input → runs Piper → validates output.
    """

    def __init__(
        self,
        piper: Piper,
        input_schema: Type[_InModel],
        output_schema: Type[_OutModel],
        strict: bool = True,
    ):
        """
        Initialize a DataMapping with Piper and schemas.

        Args:
            piper: A Piper instance for data transformation
            input_schema: Pydantic BaseModel class for input validation
            output_schema: Pydantic BaseModel class for output validation
            strict: If True, enforce strict validation
        """
        self._validate_schemas(input_schema, output_schema)

        self.piper = piper
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.strict = strict

    def forward(self, data: Any) -> _OutModel:
        """
        Transform and validate data from input to output schema.

        Args:
            data: Input data (Pydantic model instance or dict)

        Returns:
            Validated output model instance

        Raises:
            ValidationError: If input or output validation fails
        """
        # Validate and convert input
        validated_input = self._validate_input(data)

        # Convert to dict for Piper
        input_dict = self._to_dict(validated_input)

        # Apply transformation
        output_dict = self.piper(input_dict)

        # Validate and return output
        return self._validate_output(output_dict)

    def _validate_schemas(self, input_schema: Type, output_schema: Type) -> None:
        """Validate that schemas are Pydantic BaseModel classes."""
        if not self._is_pydantic_model(input_schema):
            raise TypeError(
                f"input_schema must be a Pydantic BaseModel, got {type(input_schema)}"
            )
        if not self._is_pydantic_model(output_schema):
            raise TypeError(
                f"output_schema must be a Pydantic BaseModel, got {type(output_schema)}"
            )

    def _is_pydantic_model(self, model_class: Type) -> bool:
        """Check if a class is a Pydantic BaseModel."""
        try:
            return (
                isinstance(model_class, type)
                and issubclass(model_class, BaseModel)
                and hasattr(model_class, "model_fields")
            )
        except TypeError:
            return False

    def _validate_input(self, data: Any) -> _InModel:
        """Validate input data against input schema."""
        if isinstance(data, self.input_schema):
            return data  # type: ignore[return-value]

        # Try to convert dict to model
        if isinstance(data, dict):
            return self.input_schema.model_validate(data)  # type: ignore[return-value]

        # Try direct validation
        return self.input_schema.model_validate(data)  # type: ignore[return-value]

    def _to_dict(self, model: _InModel) -> dict[str, Any]:
        """Convert Pydantic model to dictionary."""
        return model.model_dump()

    def _validate_output(self, data: dict[str, Any]) -> _OutModel:
        """Validate output data against output schema."""
        return self.output_schema.model_validate(data)  # type: ignore[return-value]
