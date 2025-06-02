"""Test the unified DataMapping class."""

from typing import Any, Optional

import chidian.partials as p
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


class TestDataMappingUnidirectional:
    """Test DataMapping in unidirectional mode (without spillover)."""

    def test_simple_mapping(self) -> None:
        """Test basic field mapping."""
        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={"subject_ref": "id", "performer": "name"},
            bidirectional=False,
        )

        patient = Patient(id="123", name="John", active=True)
        obs: Any = mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

    def test_complex_mapping(self) -> None:
        """Test mapping with transformations."""
        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={  # type: ignore
                "subject_ref": p.get("id") >> p.format_string("Patient/{}"),
                "performer": p.get("name") >> p.upper,
                "status": p.get("active")
                >> p.case({True: "active", False: "inactive"}, default="unknown"),
            },
            bidirectional=False,
        )

        patient = Patient(id="123", name="john", active=True)
        obs: Any = mapping.forward(patient)

        assert obs.subject_ref == "Patient/123"
        assert obs.performer == "JOHN"
        assert obs.status == "active"

    def test_reverse_not_available(self) -> None:
        """Test that reverse is not available in unidirectional mode."""
        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={
                "subject_ref": "id",
                "performer": "name",  # Add required field
            },
            bidirectional=False,
        )

        obs = Observation(subject_ref="123", performer="John")

        with pytest.raises(
            RuntimeError, match="reverse.*only available in bidirectional mode"
        ):
            mapping.reverse(obs)

        assert not mapping.is_reversible()
        assert not mapping.can_reverse()


class TestDataMappingBidirectional:
    """Test DataMapping in bidirectional mode (Lens)."""

    def test_simple_bidirectional(self) -> None:
        """Test basic bidirectional mapping."""
        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )

        # Forward
        patient = Patient(id="123", name="John", active=True)
        obs: Any
        obs, spillover = mapping.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

        # Check spillover
        assert len(spillover) == 1
        assert spillover._items[0]["active"] is True

        # Reverse
        recovered = mapping.reverse(obs, spillover)
        assert isinstance(recovered, Patient)
        assert recovered.id == "123"
        assert recovered.name == "John"
        assert recovered.active is True

    def test_invalid_bidirectional_mapping(self) -> None:
        """Test that non-string mappings are rejected in bidirectional mode."""
        with pytest.raises(
            TypeError, match="Bidirectional mappings must be string-to-string"
        ):
            DataMapping(
                source_model=Patient,
                target_model=Observation,
                mapping={  # type: ignore
                    "id": lambda x: x[
                        "subject_ref"
                    ]  # Function not allowed  # type: ignore
                },
                bidirectional=True,
            )

    def test_non_reversible_mapping(self) -> None:
        """Test detection of non-reversible mappings."""
        # Many-to-one mapping
        with pytest.raises(ValueError, match="not reversible.*duplicate target paths"):
            DataMapping(
                source_model=Patient,
                target_model=Observation,
                mapping={
                    "id": "subject_ref",
                    "name": "subject_ref",  # Duplicate target
                },
                bidirectional=True,
                strict=True,
            )

    def test_roundtrip(self) -> None:
        """Test lossless roundtrip transformation."""
        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )

        original = Patient(
            id="456", name="Jane", active=False, internal_notes="Important", age=30
        )

        # Forward and reverse
        target: Any
        target, spillover = mapping.forward(original)
        recovered = mapping.reverse(target, spillover)

        # Should be identical
        assert recovered.model_dump() == original.model_dump()


class TestDataMappingWithPiper:
    """Test DataMapping integration with Piper."""

    def test_piper_unidirectional(self) -> None:
        """Test Piper with unidirectional DataMapping."""

        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={"subject_ref": "id", "performer": "name"},
            bidirectional=False,
        )

        piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True)
        obs = piper(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

        # Should not be reversible
        assert not piper.can_reverse()

    def test_piper_bidirectional(self) -> None:
        """Test Piper with bidirectional DataMapping."""

        mapping = DataMapping(
            source_model=Patient,
            target_model=Observation,
            mapping={"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )

        piper: Piper = Piper(mapping)

        # Forward
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = piper(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"

        # Should be reversible
        assert piper.can_reverse()

        # Reverse
        recovered = piper.reverse(obs, spillover)
        assert recovered.id == "123"
        assert recovered.name == "John"


class TestDataMappingValidation:
    """Test validation features."""

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
                bidirectional=False,
                strict=True,
            )

        # Should work in non-strict mode
        mapping = DataMapping(
            source_model=Source,
            target_model=Target,
            mapping={"id": "id"},
            bidirectional=False,
            strict=False,
        )
        assert mapping.strict is False

    def test_type_validation(self) -> None:
        """Test that non-Pydantic models are rejected."""
        with pytest.raises(TypeError, match="must be a Pydantic v2 BaseModel"):
            DataMapping(
                source_model=dict,  # Not a Pydantic model
                target_model=BaseModel,
                mapping={},
                bidirectional=False,
            )
