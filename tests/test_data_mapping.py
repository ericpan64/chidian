"""Test the new DataMapping class and Mapper with validation modes."""

from typing import Any, Optional

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
            min_input_schemas=[Patient],
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
            min_input_schemas=[Patient],
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
            min_input_schemas=[Patient],
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
        assert isinstance(result.data, Observation)
        assert result.data.subject_ref == "123"


class TestDataMappingValidation:
    """Test DataMapping validation features."""

    def test_no_input_validation(self) -> None:
        """Test that Mapper no longer validates input (min_input_schemas is metadata-only)."""
        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            min_input_schemas=[Patient],
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        # Valid input works
        patient = Patient(id="123", name="John", active=True)
        obs = mapper(patient)
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"

        # Invalid input now works because no input validation occurs
        # Will fail on output validation due to missing required fields
        with pytest.raises(Exception):  # Output validation error
            mapper({"invalid": "data"})

    def test_output_validation(self) -> None:
        """Test that Mapper validates output against output schema."""
        # DataMapping that produces invalid output
        data_mapping = DataMapping(
            transformations={
                "invalid_field": lambda data: "value",  # Missing required fields
            },
            min_input_schemas=[Patient],
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
            min_input_schemas=[Patient],
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
            min_input_schemas=[Patient],
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
        # With output schema - should use strict mode
        data_mapping_with_schemas = DataMapping(
            transformations={
                "subject_ref": p.get("id"),
                "performer": p.get("name"),
            },
            min_input_schemas=[Patient],
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping_with_schemas)  # AUTO mode by default
        assert mapper.mode == ValidationMode.STRICT

        # Without schemas - should use flexible mode
        data_mapping_no_schemas: DataMapping[Any] = DataMapping(
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
        data_mapping: DataMapping[Any] = DataMapping(
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
        data_mapping: DataMapping[Any] = DataMapping(
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


class TestManyToOneMapping:
    """Test many-to-one mapping metadata functionality."""

    def test_min_input_schemas_metadata(self) -> None:
        """Test that min_input_schemas is stored as metadata."""

        class Encounter(BaseModel):
            id: str
            status: str
            period_start: str

        data_mapping = DataMapping(
            transformations={
                "subject_ref": lambda data: f"Patient/{data.get('patient_id', 'unknown')}",
                "encounter_ref": lambda data: f"Encounter/{data.get('encounter_id', 'unknown')}",
                "status": lambda data: data.get("status", "unknown"),
            },
            min_input_schemas=[Patient, Encounter],
            output_schema=Observation,
        )

        # Verify metadata is stored
        assert data_mapping.min_input_schemas == [Patient, Encounter]
        assert len(data_mapping.min_input_schemas) == 2

    def test_other_input_schemas_metadata(self) -> None:
        """Test that other_input_schemas is stored as metadata."""

        class Encounter(BaseModel):
            id: str
            status: str

        class Practitioner(BaseModel):
            id: str
            name: str

        data_mapping = DataMapping(
            transformations={
                "subject_ref": p.get("patient_id"),
                "performer": p.get("practitioner_name"),
                "encounter_ref": p.get("encounter_id"),
            },
            min_input_schemas=[Patient],
            other_input_schemas=[Encounter, Practitioner],
            output_schema=Observation,
        )

        # Verify metadata is stored
        assert data_mapping.min_input_schemas == [Patient]
        assert data_mapping.other_input_schemas == [Encounter, Practitioner]
        assert len(data_mapping.other_input_schemas) == 2

    def test_metadata_not_enforced_at_runtime(self) -> None:
        """Test that input schemas are not enforced during transformation."""

        class CompletelyDifferentModel(BaseModel):
            foo: str
            bar: int

        data_mapping = DataMapping(
            transformations={
                "subject_ref": lambda data: f"Patient/{data.get('totally_different_field', '123')}",
                "performer": lambda data: "Dr. Smith",
            },
            min_input_schemas=[CompletelyDifferentModel],  # This is just metadata
            output_schema=Observation,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        # Can pass any dict, not enforced to match CompletelyDifferentModel
        result = mapper(
            {"totally_different_field": "xyz", "some_other_field": "ignored"}
        )

        assert isinstance(result, Observation)
        assert result.subject_ref == "Patient/xyz"
        assert result.performer == "Dr. Smith"

    def test_empty_schemas_lists(self) -> None:
        """Test DataMapping with empty or None schema lists."""
        # Test with None (should default to empty lists)
        data_mapping1: DataMapping[Any] = DataMapping(
            transformations={
                "field1": p.get("source1"),
            },
            min_input_schemas=None,
            other_input_schemas=None,
        )

        assert data_mapping1.min_input_schemas == []
        assert data_mapping1.other_input_schemas == []

        # Test with explicit empty lists
        data_mapping2: DataMapping[Any] = DataMapping(
            transformations={
                "field2": p.get("source2"),
            },
            min_input_schemas=[],
            other_input_schemas=[],
        )

        assert data_mapping2.min_input_schemas == []
        assert data_mapping2.other_input_schemas == []

    def test_has_schemas_only_checks_output(self) -> None:
        """Test that has_schemas only checks for output_schema."""
        # With min_input_schemas but no output_schema
        data_mapping1: DataMapping[Any] = DataMapping(
            transformations={"field": p.get("source")},
            min_input_schemas=[Patient],
        )
        assert not data_mapping1.has_schemas

        # With output_schema
        data_mapping2 = DataMapping(
            transformations={"field": p.get("source")},
            output_schema=Observation,
        )
        assert data_mapping2.has_schemas

        # With both min_input_schemas and output_schema
        data_mapping3 = DataMapping(
            transformations={"field": p.get("source")},
            min_input_schemas=[Patient],
            output_schema=Observation,
        )
        assert data_mapping3.has_schemas
