"""
Helper functions for DataMapping validation and processing.
"""

from typing import Any, Type, TypeVar

from pydantic import BaseModel

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)


def validate_schemas(input_schema: Type, output_schema: Type) -> None:
    """Validate that schemas are Pydantic BaseModel classes."""
    if not is_pydantic_model(input_schema):
        raise TypeError(
            f"input_schema must be a Pydantic BaseModel, got {type(input_schema)}"
        )
    if not is_pydantic_model(output_schema):
        raise TypeError(
            f"output_schema must be a Pydantic BaseModel, got {type(output_schema)}"
        )


def is_pydantic_model(model_class: Type) -> bool:
    """Check if a class is a Pydantic BaseModel."""
    try:
        return (
            isinstance(model_class, type)
            and issubclass(model_class, BaseModel)
            and hasattr(model_class, "model_fields")
        )
    except TypeError:
        return False


def validate_input(data: Any, input_schema: Type[_InModel]) -> _InModel:
    """Validate input data against input schema."""
    if isinstance(data, input_schema):
        return data  # type: ignore[return-value]

    # Try to convert dict to model
    if isinstance(data, dict):
        return input_schema.model_validate(data)  # type: ignore[return-value]

    # Try direct validation
    return input_schema.model_validate(data)  # type: ignore[return-value]


def to_dict(model: _InModel) -> dict[str, Any]:
    """Convert Pydantic model to dictionary."""
    return model.model_dump()


def validate_output(data: dict[str, Any], output_schema: Type[_OutModel]) -> _OutModel:
    """Validate output data against output schema."""
    return output_schema.model_validate(data)  # type: ignore[return-value]
