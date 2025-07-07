"""Test the new DataMapping class as forward-only validator."""

from typing import Optional

import pytest
from chidian import DataMapping, Piper
from pydantic import BaseModel


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

    def test_simple_mapping_with_piper(self) -> None:
        """Test DataMapping with Piper for basic field mapping."""
        # Create a Piper for transformation
        piper = Piper({"subject_ref": "id", "performer": "name"})

        # Create DataMapping with Piper and schemas
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_complex_mapping_with_callable_piper(self) -> None:
        """Test DataMapping with callable Piper for complex transformations."""

        def transform_fn(data: dict) -> dict:
            return {
                "subject_ref": f"Patient/{data['id']}",
                "performer": data["name"].upper(),
                "status": "active" if data["active"] else "inactive",
            }

        piper = Piper(transform_fn)

        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="john", active=True)
        obs = mapping.forward(patient)

        assert obs.subject_ref == "Patient/123"
        assert obs.performer == "JOHN"
        assert obs.status == "active"

    def test_no_reverse_functionality(self) -> None:
        """Test that DataMapping doesn't support reverse operations."""
        piper = Piper({"subject_ref": "id", "performer": "name"})
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Should not have reverse method
        assert not hasattr(mapping, "reverse")

        # Should not have can_reverse method
        assert not hasattr(mapping, "can_reverse")


class TestDataMappingValidation:
    """Test DataMapping validation features."""

    def test_input_validation(self) -> None:
        """Test that DataMapping validates input against input schema."""
        piper = Piper({"subject_ref": "id", "performer": "name"})
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Valid input works
        patient = Patient(id="123", name="John", active=True)
        obs = mapping.forward(patient)
        assert obs.subject_ref == "123"

        # Invalid input should raise ValidationError
        with pytest.raises(Exception):  # Pydantic ValidationError
            mapping.forward({"invalid": "data"})

    def test_output_validation(self) -> None:
        """Test that DataMapping validates output against output schema."""

        # Piper that produces invalid output
        def bad_transform(data: dict) -> dict:
            return {"invalid_field": "value"}  # Missing required fields

        piper = Piper(bad_transform)
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)

        # Should raise ValidationError due to invalid output
        with pytest.raises(Exception):  # Pydantic ValidationError
            mapping.forward(patient)

    def test_schema_validation(self) -> None:
        """Test that DataMapping validates schema types."""
        piper = Piper({"output": "input"})

        # Non-Pydantic schema should raise TypeError
        with pytest.raises(TypeError):
            DataMapping(
                piper=piper,
                input_schema=dict,  # type: ignore  # Not a Pydantic model
                output_schema=Observation,
            )

        with pytest.raises(TypeError):
            DataMapping(
                piper=piper,
                input_schema=Patient,
                output_schema=dict,  # type: ignore  # Not a Pydantic model
            )

    def test_dict_input_with_strict_mode(self) -> None:
        """Test handling of dict input in strict mode."""
        piper = Piper({"subject_ref": "id", "performer": "name"})
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
            strict=True,
        )

        # Dict input should be validated and converted
        dict_input = {"id": "123", "name": "John", "active": True}
        obs = mapping.forward(dict_input)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_non_strict_mode(self) -> None:
        """Test behavior in non-strict mode."""
        piper = Piper({"subject_ref": "id", "performer": "name"})
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
            strict=False,
        )

        # Should still work with valid input
        patient = Patient(id="123", name="John", active=True)
        obs = mapping.forward(patient)
        assert obs.subject_ref == "123"


class TestDataMappingWithPiper:
    """Test DataMapping integration with different Piper types."""

    def test_with_dict_piper(self) -> None:
        """Test DataMapping with dict-based Piper."""
        piper = Piper({"subject_ref": "id", "performer": "name"})
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_with_callable_piper(self) -> None:
        """Test DataMapping with callable Piper."""

        def transform_fn(data: dict) -> dict:
            return {
                "subject_ref": data["id"],
                "performer": data["name"],
                "status": "processed",
            }

        piper = Piper(transform_fn)
        mapping = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        patient = Patient(id="123", name="John", active=True)
        obs = mapping.forward(patient)

        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        assert obs.status == "processed"

    def test_piper_independence(self) -> None:
        """Test that Piper works independently of DataMapping."""
        piper = Piper({"output": "input"})

        # Piper should work standalone
        result = piper({"input": "test"})
        assert result["output"] == "test"

        # Same Piper can be used with DataMapping
        _ = DataMapping(
            piper=piper,
            input_schema=Patient,
            output_schema=Observation,
        )

        # Both should work independently
        direct_result = piper({"input": "direct"})
        assert direct_result["output"] == "direct"
