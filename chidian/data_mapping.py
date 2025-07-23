"""
DataMapping class as forward-only validator wrapper around Mapper.
"""

from typing import Any, Generic, Type, TypeVar

from pydantic import BaseModel

from .lib.data_mapping_helpers import (
    to_dict,
    validate_input,
    validate_output,
    validate_schemas,
)
from .mapper import Mapper

# Define generic type variables bounded to BaseModel
_InModel = TypeVar("_InModel", bound=BaseModel)
_OutModel = TypeVar("_OutModel", bound=BaseModel)


class DataMapping(Generic[_InModel, _OutModel]):
    """
    A forward-only data mapping with schema validation.

    Takes a Mapper for transformation logic and Pydantic schemas for validation.
    Validates input → runs Mapper → validates output.
    """

    def __init__(
        self,
        mapper: Mapper,
        input_schema: Type[_InModel],
        output_schema: Type[_OutModel],
        strict: bool = True,
    ):
        """
        Initialize a DataMapping with Mapper and schemas.

        Args:
            mapper: A Mapper instance for data transformation
            input_schema: Pydantic BaseModel class for input validation
            output_schema: Pydantic BaseModel class for output validation
            strict: If True, enforce strict validation
        """
        validate_schemas(input_schema, output_schema)

        self.mapper = mapper
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
        validated_input = validate_input(data, self.input_schema)

        # Convert to dict for Mapper
        input_dict = to_dict(validated_input)

        # Apply transformation
        output_dict = self.mapper(input_dict)

        # Validate and return output
        return validate_output(output_dict, self.output_schema)
