"""Test the new DataMapping class as forward-only validator."""

from typing import Optional

import pytest
from pydantic import BaseModel

import chidian.partials as p
from chidian import DataMapping, Mapper


# Test models
class Patient(BaseModel):
    id: str
    name: str
    active: bool
    internal_notes: Optional[str] = None
    age: Optional[int] = None


class Observation(BaseModel):
    subject_ref: str
    performer: str
    status: Optional[str] = None


class TestDataMappingBasic:
    """Test basic DataMapping functionality as forward-only validator."""

    def test_simple_mapping_with_mapper(self) -> None:
        """Test DataMapping with Mapper for basic field mapping."""
        # Create a Mapper for transformation
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )

        # Create DataMapping with Mapper and schemas
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = data_mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_complex_mapping_with_callable_mapper(self) -> None:
        """Test DataMapping with callable transformations in Mapper."""
        mapping = {
            "subject_ref": lambda data: f"Patient/{data['id']}",
            "performer": lambda data: data["name"].upper(),
            "status": lambda data: "active" if data["active"] else "inactive",
        }

        mapper = Mapper(mapping)

        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="john", active=True)
        obs = data_mapping.forward(patient)

        assert obs.subject_ref == "Patient/123"
        assert obs.performer == "JOHN"
        assert obs.status == "active"

    def test_no_reverse_functionality(self) -> None:
        """Test that DataMapping doesn't support reverse operations."""
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Should not have reverse method
        assert not hasattr(data_mapping, "reverse")

        # Should not have can_reverse method
        assert not hasattr(data_mapping, "can_reverse")


class TestDataMappingValidation:
    """Test DataMapping validation features."""

    def test_input_validation(self) -> None:
        """Test that DataMapping validates input against input schema."""
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Valid input works
        patient = Patient(id="123", name="John", active=True)
        obs = data_mapping.forward(patient)
        assert obs.subject_ref == "123"

        # Invalid input should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            data_mapping.forward({"invalid": "data"})

    def test_output_validation(self) -> None:
        """Test that DataMapping validates output against output schema."""

        # Mapper that produces invalid output
        mapping = {
            "invalid_field": lambda data: "value",  # Missing required fields
        }

        mapper = Mapper(mapping)
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)

        # Should raise ValidationError due to invalid output
        with pytest.raises(Exception):  # Pydantic ValidationError
            data_mapping.forward(patient)

    def test_schema_validation(self) -> None:
        """Test that DataMapping validates schema types."""
        mapper = Mapper({"output": p.get("input")})

        # Non-Pydantic schema should raise TypeError
        with pytest.raises(TypeError):
            DataMapping(
                mapper=mapper,
                input_schema=dict,  # type: ignore  # Not a Pydantic model
                output_schema=Observation,
            )

        with pytest.raises(TypeError):
            DataMapping(
                mapper=mapper,
                input_schema=Patient,
                output_schema=dict,  # type: ignore  # Not a Pydantic model
            )

    def test_dict_input_with_strict_mode(self) -> None:
        """Test handling of dict input in strict mode."""
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
            strict=True,
        )

        # Dict input should be validated and converted
        dict_input = {"id": "123", "name": "John", "active": True}
        obs = data_mapping.forward(dict_input)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_non_strict_mode(self) -> None:
        """Test behavior in non-strict mode."""
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
            strict=False,
        )

        # Should still work with valid input
        patient = Patient(id="123", name="John", active=True)
        obs = data_mapping.forward(patient)
        assert obs.subject_ref == "123"


class TestDataMappingWithMapper:
    """Test DataMapping integration with different Mapper types."""

    def test_with_dict_mapper(self) -> None:
        """Test DataMapping with dict-based Mapper."""
        mapper = Mapper(
            {
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = data_mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_with_callable_mapper(self) -> None:
        """Test DataMapping with callable transformations in Mapper."""
        mapping = {
            "subject_ref": lambda data: data["id"],
            "performer": lambda data: data["name"],
            "status": lambda data: "processed",
        }

        mapper = Mapper(mapping)
        data_mapping = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = data_mapping.forward(patient)

        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        assert obs.status == "processed"

    def test_mapper_independence(self) -> None:
        """Test that Mapper works independently of DataMapping."""
        mapper = Mapper({"output": p.get("input")})

        # Mapper should work standalone
        result = mapper({"input": "test"})
        assert result["output"] == "test"

        # Same Mapper can be used with DataMapping
        _ = DataMapping(
            mapper=mapper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Both should work independently
        direct_result = mapper({"input": "direct"})
        assert direct_result["output"] == "direct"
