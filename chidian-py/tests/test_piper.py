"""Comprehensive tests for Piper mapping scenarios."""

from typing import Any

import chidian.partials as p
import pytest
from chidian import DataMapping, Piper, RecordSet, get

from tests.structstest import (
    Observation,
    Patient,
    PersonSource,
    PersonTarget,
    ProcessedData,
    SourceData,
    SourceModel,
    TargetModel,
)


class TestPiperBasic:
    """Test basic Piper functionality with DataMapping."""

    def test_simple_mapping(self, simple_data: dict[str, Any]) -> None:
        """Test basic Piper functionality with callable mapping."""

        def mapping(data: dict) -> dict:
            return {
                "patient_id": get(data, "data.patient.id"),
                "is_active": get(data, "data.patient.active"),
                "status": "processed",
            }

        data_mapping = DataMapping(SourceData, ProcessedData, mapping)
        piper: Piper = Piper(data_mapping)
        result = piper(SourceData.model_validate(simple_data))

        assert isinstance(result, ProcessedData)
        assert result.patient_id == "abc123"
        assert result.is_active
        assert result.status == "processed"

    def test_callable_mapping_with_partials(self) -> None:
        """Test DataMapping with callable mapping using partials API."""

        data = {
            "firstName": "John",
            "lastName": "Doe",
            "status": "active",
            "codes": ["A", "B", "C"],
            "address": "123 Main St|Boston|02101",
        }

        def mapper(data: dict) -> dict:
            # Use new partials API
            name_template = p.template("{} {}")
            status_classifier = p.get("status") >> p.case(
                {"active": "✓ Active", "inactive": "✗ Inactive"}, default="Unknown"
            )
            city_extractor = p.get("address") >> p.split("|") >> p.at_index(1)

            return {
                "name": name_template(get(data, "firstName"), get(data, "lastName")),
                "status_display": status_classifier(data),
                "all_codes": p.flatten(["codes"], delimiter=", ")(data),
                "city": city_extractor(data),
                "backup_name": p.coalesce("nickname", "firstName", default="Guest")(
                    data
                ),
            }

        data_mapping = DataMapping(PersonSource, PersonTarget, mapper)
        piper: Piper = Piper(data_mapping)
        result = piper(PersonSource.model_validate(data))

        assert isinstance(result, PersonTarget)
        assert result.name == "John Doe"
        assert result.status_display == "✓ Active"
        assert result.all_codes == "A, B, C"
        assert result.city == "Boston"
        assert result.backup_name == "John"


class TestPiperUnidirectional:
    """Test Piper in unidirectional mode (View)."""

    def test_typed_piper_view_creation(self) -> None:
        """Test creating a typed Piper in View mode."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        assert isinstance(piper, Piper)
        assert piper._mode == "view"
        assert piper.input_type == Patient
        assert piper.output_type == Observation
        assert piper.can_reverse() is False

    def test_typed_piper_view_forward(self) -> None:
        """Test forward transformation with View."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True, age=45)

        # Forward should return just the target object (no spillover)
        obs: Any = piper.forward(patient)

        # In non-strict mode, may return dict instead of typed object
        if isinstance(obs, dict):
            assert obs.get("subject_ref") == "123"
            assert obs.get("performer") == "John"
        else:
            assert isinstance(obs, Observation)
            assert obs.subject_ref == "123"
            assert obs.performer == "John"

    def test_typed_piper_view_call_syntax(self) -> None:
        """Test that View can be called directly without .forward()."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True)

        # Should work same as .forward()
        obs1: Any = piper(patient)
        obs2: Any = piper.forward(patient)

        # Both should return the same type and content
        if isinstance(obs1, dict) and isinstance(obs2, dict):
            assert obs1.get("subject_ref") == obs2.get("subject_ref") == "123"
        elif hasattr(obs1, "subject_ref") and hasattr(obs2, "subject_ref"):
            assert obs1.subject_ref == obs2.subject_ref == "123"

    def test_typed_piper_view_reverse_fails(self) -> None:
        """Test that reverse transformation fails with View."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        obs = Observation(subject_ref="123", performer="John")

        # Reverse should fail
        with pytest.raises(ValueError, match="Reverse transformation only available"):
            piper.reverse(obs, RecordSet())

        assert piper.can_reverse() is False

    def test_typed_piper_view_type_validation(self) -> None:
        """Test type validation with typed Piper."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=True,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        # Correct type works
        patient = Patient(id="123", name="John", active=True)
        obs = piper.forward(patient)
        assert isinstance(obs, Observation)

        # Wrong type should fail
        with pytest.raises(TypeError):
            piper.forward("not a patient")

    def test_create_unidirectional_piper(self) -> None:
        """Test creating unidirectional piper."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        assert isinstance(piper, Piper)
        assert piper._mode == "view"
        assert piper.can_reverse() is False


class TestPiperBidirectional:
    """Test Piper in bidirectional mode (Lens)."""

    def test_typed_piper_lens_creation(self) -> None:
        """Test creating a typed Piper in Lens mode."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        assert isinstance(piper, Piper)
        assert piper._mode == "lens"
        assert piper.input_type == Patient
        assert piper.output_type == Observation
        assert piper.can_reverse() is True

    def test_typed_piper_lens_forward(self) -> None:
        """Test forward transformation with Lens."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True, age=45)

        # Forward should return target object AND spillover
        obs, spillover = piper.forward(patient)

        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"

        assert isinstance(spillover, RecordSet)
        spillover_data = spillover._items[0]
        assert spillover_data["active"] is True
        assert spillover_data["age"] == 45

    def test_typed_piper_lens_reverse(self) -> None:
        """Test reverse transformation with Lens."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True, "age": 45}])

        patient = piper.reverse(obs, spillover)

        assert isinstance(patient, Patient)
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
        assert patient.age == 45

    def test_typed_piper_lens_roundtrip(self) -> None:
        """Test lossless roundtrip with Lens."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        original = Patient(id="123", name="John", active=True, age=45)

        # Forward
        obs, spillover = piper.forward(original)

        # Reverse
        recovered = piper.reverse(obs, spillover)

        assert recovered == original

    def test_typed_piper_lens_call_syntax(self) -> None:
        """Test Piper with Lens can be called directly."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True)
        obs, spillover = piper(patient)  # Should work same as forward()

        assert obs.subject_ref == "123"
        assert spillover is not None

    def test_create_bidirectional_piper(self) -> None:
        """Test creating bidirectional piper."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        assert isinstance(piper, Piper)
        assert piper._mode == "lens"
        assert piper.can_reverse() is True


class TestPiperStrictMode:
    """Test Piper strict mode behavior."""

    def test_piper_inherits_data_mapping_properties(self) -> None:
        """Test that Piper inherits properties from DataMapping."""

        def mapper(data: dict) -> dict:
            return {"result": data.get("value")}

        data_mapping = DataMapping(SourceModel, TargetModel, mapper, strict=False)
        piper: Piper = Piper(data_mapping)

        assert piper.input_type is SourceModel
        assert piper.output_type is TargetModel
        assert piper.strict is False

    def test_lens_inherits_strict_mode(self) -> None:
        """Test that Piper inherits strict mode from mapping."""
        mapping_strict = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            strict=True,
            bidirectional=True,
        )
        mapping_nonstrict = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            strict=False,
            bidirectional=False,
        )

        piper_strict: Piper = Piper(mapping_strict)
        piper_nonstrict: Piper = Piper(mapping_nonstrict)

        assert piper_strict.strict is True
        assert piper_nonstrict.strict is False

    def test_strict_input_validation(self) -> None:
        """Test strict input type validation with mapping."""
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            strict=True,
            bidirectional=True,
        )
        piper: Piper = Piper(mapping)

        # Correct type works
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = piper.forward(patient)
        assert obs.subject_ref == "123"

        # Wrong type should fail in strict mode
        with pytest.raises(TypeError):
            piper.forward("not a patient")


class TestPiperIntegration:
    """Test Piper integration scenarios."""

    def test_type_safety_prevents_chaining_errors(self) -> None:
        """Test that type safety prevents incompatible chaining."""
        # Create two pipers with incompatible types
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        piper: Piper = Piper(mapping)

        # This would be a type error if we tried to chain with a different input type
        # (In real usage, mypy/type checker would catch this)
        assert piper.input_type == Patient
        assert piper.output_type == Observation

    def test_mixed_mode_workflow(self) -> None:
        """Test workflow mixing View and Lens based pipers."""
        # Step 1: Use View for one-way transformation
        mapping = DataMapping(
            Patient,
            Observation,
            {"subject_ref": "id", "performer": "name"},
            strict=False,
            bidirectional=False,
        )
        unidirectional_piper: Piper = Piper(mapping)

        # Step 2: Use Lens for bidirectional transformation
        mapping = DataMapping(
            Patient,
            Observation,
            {"id": "subject_ref", "name": "performer"},
            bidirectional=True,
        )
        bidirectional_piper: Piper = Piper(mapping)

        patient = Patient(id="123", name="John", active=True, age=45)

        # View transformation (one-way) - may return dict in non-strict mode
        obs_unidirectional: Any = unidirectional_piper.forward(patient)
        if isinstance(obs_unidirectional, dict):
            assert obs_unidirectional.get("subject_ref") == "123"
        elif hasattr(obs_unidirectional, "subject_ref"):
            assert obs_unidirectional.subject_ref == "123"

        # Lens transformation (bidirectional)
        obs_bidirectional, spillover = bidirectional_piper.forward(patient)
        recovered = bidirectional_piper.reverse(obs_bidirectional, spillover)
        assert recovered == patient
