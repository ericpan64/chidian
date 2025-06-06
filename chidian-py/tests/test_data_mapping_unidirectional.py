"""Tests for DataMapping in unidirectional mode (formerly View)."""

from typing import Any, Optional

import chidian.partials as p
import pytest
from chidian import DataMapping
from pydantic import BaseModel


class TestDataMappingUnidirectionalBasic:
    """Test basic DataMapping functionality in unidirectional mode."""

    def test_simple_mapping(self) -> None:
        """Test basic field mapping with Pydantic models."""

        class Source(BaseModel):
            id: str
            name: str

        class Target(BaseModel):
            person_id: str
            display_name: str

        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={"person_id": "id", "display_name": "name"},
            bidirectional=False,
        )

        source = Source(id="123", name="John Doe")
        result: Any = mapping.forward(source)

        assert isinstance(result, Target)
        assert result.person_id == "123"
        assert result.display_name == "John Doe"

    def test_nested_paths(self) -> None:
        """Test mapping with nested paths."""

        class Source(BaseModel):
            subject: dict
            valueQuantity: dict

        class Target(BaseModel):
            patient_id: str
            value: float

        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={"patient_id": "subject.reference", "value": "valueQuantity.value"},
            bidirectional=False,
        )

        source = Source(
            subject={"reference": "Patient/123"},
            valueQuantity={"value": 140.0, "unit": "mmHg"},
        )
        result: Any = mapping.forward(source)

        assert result.patient_id == "Patient/123"
        assert result.value == 140.0

    def test_with_transformations(self) -> None:
        """Test mapping with chainable transformations."""

        class Source(BaseModel):
            name: str
            reference: str

        class Target(BaseModel):
            name_upper: str
            id: int

        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={  # type: ignore
                "name_upper": p.get("name") >> p.upper,
                "id": p.get("reference") >> p.split("/") >> p.last >> p.to_int,
            },
            bidirectional=False,
        )

        source = Source(name="john doe", reference="Patient/456")
        result: Any = mapping.forward(source)

        assert result.name_upper == "JOHN DOE"
        assert result.id == 456


class TestDataMappingUnidirectionalValidation:
    """Test DataMapping validation and error handling."""

    def test_strict_mode_validation(self) -> None:
        """Test strict mode enforces required fields."""

        class Source(BaseModel):
            id: str

        class Target(BaseModel):
            id: str
            required_field: str  # Required but not mapped

        # Should raise in strict mode
        with pytest.raises(ValueError, match="Missing required target fields"):
            DataMapping(
                source_model=Source,
                target_model=Target,
                mapping={"id": "id"},
                strict=True,
            )

        # Should work in non-strict mode
        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={"id": "id"},
            strict=False,
            bidirectional=False,
        )
        assert mapping.strict is False

    def test_type_validation(self) -> None:
        """Test that non-Pydantic models are rejected."""
        with pytest.raises(TypeError, match="must be a Pydantic v2 BaseModel"):
            DataMapping(
                source_model=dict,  # Not a Pydantic model
                target_model=BaseModel,
                mapping={},
            )

    def test_error_handling(self) -> None:
        """Test error handling in mappings."""

        class Source(BaseModel):
            data: dict

        class Target(BaseModel):
            safe: Optional[str] = None
            error: Optional[str] = None

        # Non-strict mode handles errors gracefully
        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={  # type: ignore
                "safe": "data.value",
                "error": p.ChainableFn(lambda x: 1 / 0),  # Will raise
            },
            strict=False,
            bidirectional=False,
        )

        source = Source(data={"value": "test"})
        result: Any = mapping.forward(source)

        assert result.safe == "test"
        assert result.error is None  # Error was caught


class TestDataMappingUnidirectionalRealWorld:
    """Test real-world transformation scenarios."""

    def test_fhir_to_flat_structure(self, fhir_observation: Any) -> None:
        """Test transforming nested FHIR to flat structure."""

        class FHIRObservation(BaseModel):
            id: str
            subject: dict
            code: dict
            valueQuantity: Optional[dict] = None

        class FlatObservation(BaseModel):
            observation_id: str
            patient_id: str
            loinc_code: str
            value: Optional[float] = None
            unit: Optional[str] = None

        mapping = DataMapping(
            source_model=FHIRObservation,
            target_model=FlatObservation,
            mapping={  # type: ignore
                "observation_id": "id",
                "patient_id": p.get("subject.reference") >> p.split("/") >> p.last,
                "loinc_code": "code.coding[0].code",
                "value": "valueQuantity.value",
                "unit": "valueQuantity.unit",
            },
            bidirectional=False,
        )

        source = FHIRObservation(**fhir_observation)
        result: Any = mapping.forward(source)

        assert result.observation_id == "obs-123"
        assert result.patient_id == "456"
        assert result.loinc_code == "8480-6"
        assert result.value == 140.0
        assert result.unit == "mmHg"
