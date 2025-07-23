"""Test the new DataMapping class and Mapper with validation modes."""

from typing import Optional

import pytest
from pydantic import BaseModel

import chidian.partials as p
from chidian import DataMapping, Mapper, MapperResult, ValidationMode


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
        # Create a DataMapping for transformation
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        # Create Mapper with DataMapping
        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        patient = Patient(id="123", name="John", active=True)
        obs = mapper(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_complex_mapping_with_callable_mapper(self) -> None:
        """Test DataMapping with callable transformations."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": lambda data: f"Patient/{data['id']}",
                "performer": lambda data: data["name"].upper(),
                "status": lambda data: "active" if data["active"] else "inactive",
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        patient = Patient(id="123", name="john", active=True)
        obs = mapper(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "Patient/123"
        assert obs.performer == "JOHN"
        assert obs.status == "active"

    def test_validation_modes(self) -> None:
        """Test different validation modes."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        # Test strict mode
        strict_mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)
        patient = Patient(id="123", name="John", active=True)
        obs = strict_mapper(patient)
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"

        # Test flexible mode
        flexible_mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)
        result = flexible_mapper(patient)
        assert isinstance(result, MapperResult)
        assert not result.has_issues
        assert result.data.subject_ref == "123"


class TestDataMappingValidation:
    """Test DataMapping validation features."""

    def test_input_validation(self) -> None:
        """Test that Mapper validates input against input schema."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        # Valid input works
        patient = Patient(id="123", name="John", active=True)
        obs = mapper(patient)
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"

        # Invalid input should raise ValidationError in strict mode
        with pytest.raises(Exception):  # Pydantic ValidationError
            mapper({"invalid": "data"})

    def test_output_validation(self) -> None:
        """Test that Mapper validates output against output schema."""
        # DataMapping that produces invalid output
        data_mapping = DataMapping(
            transformations={
                "invalid_field": lambda data: "value",  # Missing required fields
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)
        patient = Patient(id="123", name="John", active=True)

        # Should raise ValidationError due to invalid output in strict mode
        with pytest.raises(Exception):  # Pydantic ValidationError
            mapper(patient)

    def test_flexible_mode_validation(self) -> None:
        """Test flexible mode collects validation errors."""
        # DataMapping that produces invalid output
        data_mapping = DataMapping(
            transformations={
                "invalid_field": lambda data: "value",  # Missing required fields
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)
        patient = Patient(id="123", name="John", active=True)

        # Should return MapperResult with issues
        result = mapper(patient)
        assert isinstance(result, MapperResult)
        assert result.has_issues
        assert len(result.issues) > 0
        assert result.issues[0].stage == "output"

    def test_dict_input_with_strict_mode(self) -> None:
        """Test handling of dict input in strict mode."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        # Dict input should be validated and converted
        dict_input = {"id": "123", "name": "John", "active": True}
        obs = mapper(dict_input)
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_auto_mode(self) -> None:
        """Test auto mode behavior."""
        # With schemas - should use strict mode
        data_mapping_with_schemas = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            input_schema=Patient,
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping_with_schemas)  # AUTO mode by default
        assert mapper.mode == ValidationMode.STRICT

        # Without schemas - should use flexible mode
        data_mapping_no_schemas = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )

        mapper2 = Mapper(data_mapping_no_schemas)  # AUTO mode by default
        assert mapper2.mode == ValidationMode.FLEXIBLE


class TestDataMappingWithoutSchemas:
    """Test DataMapping without schemas (pure transformation)."""

    def test_pure_transformation(self) -> None:
        """Test DataMapping as pure transformation without schemas."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            }
        )

        # Direct transformation
        result = data_mapping.transform({"id": "123", "name": "John"})
        assert result["subject_ref"] == "123"
        assert result["performer"] == "John"

    def test_with_flexible_mapper(self) -> None:
        """Test DataMapping without schemas using flexible Mapper."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": lambda data: f"Patient/{data.get('id', 'unknown')}",
                "performer": lambda data: data.get("name", "Unknown"),
                "status": lambda data: "processed",
            }
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)

        # Should work with incomplete data
        result = mapper({"id": "123"})
        assert isinstance(result, MapperResult)
        assert result.data["subject_ref"] == "Patient/123"
        assert result.data["performer"] == "Unknown"
        assert result.data["status"] == "processed"

    def test_mapper_result_interface(self) -> None:
        """Test MapperResult interface."""
        data_mapping = DataMapping(
            transformations={
                "missing_field": p.get("nonexistent"),
            },
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)
        result = mapper({"id": "123"})

        assert isinstance(result, MapperResult)
        assert result.has_issues

        # Test raise_if_issues
        with pytest.raises(Exception):
            result.raise_if_issues()
