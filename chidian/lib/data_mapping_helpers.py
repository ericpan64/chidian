"""
Helper functions for DataMapping validation and processing.
"""

from typing import Any, Type, TypeVar

from pydantic import BaseModel

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)


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


def to_dict(model: _InModel) -> dict[str, Any]:
    """Convert Pydantic model to dictionary."""
    return model.model_dump()


def validate_output(data: dict[str, Any], output_schema: Type[_OutModel]) -> _OutModel:
    """Validate output data against output schema."""
    return output_schema.model_validate(data)  # type: ignore[return-value]
