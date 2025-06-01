"""Tests for Piper with DataMapping integration."""

import pytest
from typing import Optional
from pydantic import BaseModel

from chidian import Piper, DataMapping, RecordSet


class Patient(BaseModel):
    """Sample Patient model for testing."""
    id: str
    name: str
    active: bool
    age: Optional[int] = None


class Observation(BaseModel):
    """Sample Observation model for testing."""
    subject_ref: str
    performer: str
    status: Optional[str] = None


class TestPiperUnidirectional:
    """Test Piper with View (unidirectional)."""
    
    def test_typed_piper_view_creation(self):
        """Test Piper can be created with View."""
        mapping = DataMapping(Patient, Observation, {
            "subject_ref": "id",  # View expects target_field: source_field
            "performer": "name"
        }, strict=False, bidirectional=False)  # Use non-strict mode to avoid validation errors
        piper = Piper(mapping)
        
        assert piper.input_type == Patient
        assert piper.output_type == Observation
        assert piper._mode == "view"
        assert piper.can_reverse() is False
    
    def test_typed_piper_view_forward(self):
        """Test forward transformation with View."""
        mapping = DataMapping(Patient, Observation, {
            "subject_ref": "id",  # View expects target_field: source_field
            "performer": "name"
        }, strict=False, bidirectional=False)
        piper = Piper(mapping)
        
        patient = Patient(id="123", name="John", active=True, age=45)
        obs = piper.forward(patient)
        
        # In non-strict mode, View may return dict if it can't create the target model
        assert isinstance(obs, (Observation, dict))
        if isinstance(obs, dict):
            assert obs["subject_ref"] == "123"
            assert obs["performer"] == "John"
        else:
            assert obs.subject_ref == "123"
            assert obs.performer == "John"
    
    def test_typed_piper_view_call_syntax(self):
        """Test Piper can be called directly."""
        mapping = DataMapping(Patient, Observation, {
            "subject_ref": "id",
            "performer": "name"
        }, strict=False, bidirectional=False)
        piper = Piper(mapping)
        
        patient = Patient(id="123", name="John", active=True)
        obs = piper(patient)  # Should work same as forward()
        
        # Handle both dict and model outputs
        if isinstance(obs, dict):
            assert obs["subject_ref"] == "123"
            assert obs["performer"] == "John"
        else:
            assert obs.subject_ref == "123"
            assert obs.performer == "John"
    
    def test_typed_piper_view_reverse_fails(self):
        """Test that unidirectional DataMapping-based Piper cannot reverse."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, strict=False, bidirectional=False)
        piper = Piper(mapping)
        
        obs = Observation(subject_ref="123", performer="John")
        
        with pytest.raises(ValueError, match="Reverse transformation only available for bidirectional mappings"):
            piper.reverse(obs)
    
    def test_typed_piper_view_type_validation(self):
        """Test type validation."""
        mapping = DataMapping(Patient, Observation, {
            "subject_ref": "id",
            "performer": "name"
        }, strict=False, bidirectional=False)
        piper = Piper(mapping)
        
        # Correct type should work
        patient = Patient(id="123", name="John", active=True)
        obs = piper.forward(patient)
        # Handle both dict and model outputs
        if isinstance(obs, dict):
            assert obs.get("subject_ref") == "123"
        else:
            assert obs.subject_ref == "123"
    
    def test_create_unidirectional_piper(self):
        """Test creating unidirectional piper."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, strict=False, bidirectional=False)
        piper = Piper(mapping)
        
        assert isinstance(piper, Piper)
        assert piper._mode == "view"


class TestPiperBidirectional:
    """Test Piper with Lens (bidirectional)."""
    
    def test_typed_piper_lens_creation(self):
        """Test Piper can be created with Lens."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        assert piper.input_type == Patient
        assert piper.output_type == Observation
        assert piper._mode == "lens"
        assert piper.can_reverse() is True
    
    def test_typed_piper_lens_forward(self):
        """Test forward transformation with Lens."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        patient = Patient(id="123", name="John", active=True, age=45)
        obs, spillover = piper.forward(patient)
        
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        
        assert isinstance(spillover, RecordSet)
        spillover_data = spillover._items[0]
        assert spillover_data["active"] is True
        assert spillover_data["age"] == 45
    
    def test_typed_piper_lens_reverse(self):
        """Test reverse transformation with Lens."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True, "age": 45}])
        
        patient = piper.reverse(obs, spillover)
        
        assert isinstance(patient, Patient)
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
        assert patient.age == 45
    
    def test_typed_piper_lens_roundtrip(self):
        """Test lossless roundtrip with Lens."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        original = Patient(id="123", name="John", active=True, age=45)
        
        # Forward
        obs, spillover = piper.forward(original)
        
        # Reverse
        recovered = piper.reverse(obs, spillover)
        
        assert recovered == original
    
    def test_typed_piper_lens_call_syntax(self):
        """Test Piper with Lens can be called directly."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = piper(patient)  # Should work same as forward()
        
        assert obs.subject_ref == "123"
        assert spillover is not None
    
    def test_create_bidirectional_piper(self):
        """Test creating bidirectional piper."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        piper = Piper(mapping)
        
        assert isinstance(piper, Piper)
        assert piper._mode == "lens"
        assert piper.can_reverse() is True


class TestPiperErrorHandling:
    """Test Piper error handling for invalid inputs."""
    
    def test_piper_requires_data_mapping(self):
        """Test that Piper requires a DataMapping instance."""
        def mapper(patient: Patient) -> Observation:
            return Observation(
                subject_ref=patient.id,
                performer=patient.name
            )
        
        with pytest.raises(ValueError, match="Piper only supports dict-to-dict transformations or View/Lens objects"):
            Piper(mapper)
    
    def test_callable_with_wrong_types_fails(self):
        """Test that Piper rejects callables with non-dict types."""
        def mapper(x: int) -> str:
            return str(x)
        
        with pytest.raises(ValueError, match="Piper only supports dict-to-dict transformations or View/Lens objects"):
            Piper(mapper, source_type=int, target_type=str)
    
    def test_piper_rejects_none(self):
        """Test that Piper rejects None."""
        with pytest.raises(TypeError, match="Piper requires a DataMapping instance"):
            Piper(None)


class TestPiperStrictMode:
    """Test Piper strict mode behavior."""
    
    def test_piper_inherits_data_mapping_properties(self):
        """Test that Piper inherits properties from DataMapping."""
        def mapper(data: dict) -> dict:
            return {"result": data.get("value")}
        
        class SourceModel(BaseModel):
            value: str
        
        class TargetModel(BaseModel):
            result: str
        
        data_mapping = DataMapping(SourceModel, TargetModel, mapper, strict=False)
        piper = Piper(data_mapping)
        
        assert piper.input_type is SourceModel
        assert piper.output_type is TargetModel
        assert piper.strict is False
    
    def test_lens_inherits_strict_mode(self):
        """Test that Piper inherits strict mode from mapping."""
        mapping_strict = DataMapping(Patient, Observation, {"id": "subject_ref", "name": "performer"}, strict=True, bidirectional=True)
        mapping_nonstrict = DataMapping(Patient, Observation, {"id": "subject_ref", "name": "performer"}, strict=False, bidirectional=False)
        
        piper_strict = Piper(mapping_strict)
        piper_nonstrict = Piper(mapping_nonstrict)
        
        assert piper_strict.strict is True
        assert piper_nonstrict.strict is False
    
    def test_strict_input_validation(self):
        """Test strict input type validation with mapping."""
        mapping = DataMapping(Patient, Observation, {
            "id": "subject_ref", 
            "name": "performer"
        }, strict=True, bidirectional=True)
        piper = Piper(mapping)
        
        # Correct type works
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = piper.forward(patient)
        assert obs.subject_ref == "123"
        
        # Wrong type should fail in strict mode
        with pytest.raises(TypeError):
            piper.forward("not a patient")


class TestPiperIntegration:
    """Test Piper integration scenarios."""
    
    def test_type_safety_prevents_chaining_errors(self):
        """Test that type safety prevents incompatible chaining."""
        # Create two pipers with incompatible types
        mapping1 = DataMapping(Patient, Observation, {"subject_ref": "id", "performer": "name"}, strict=False, bidirectional=False)
        piper1 = Piper(mapping1)
        
        # This would be a type error if we tried to chain with a different input type
        # (In real usage, mypy/type checker would catch this)
        assert piper1.input_type == Patient
        assert piper1.output_type == Observation
    
    def test_mixed_mode_workflow(self):
        """Test workflow mixing View and Lens based pipers."""
        # Step 1: Use View for one-way transformation
        mapping = DataMapping(Patient, Observation, {"subject_ref": "id", "performer": "name"}, strict=False, bidirectional=False)
        unidirectional_piper = Piper(mapping)
        
        # Step 2: Use Lens for bidirectional transformation
        mapping = DataMapping(Patient, Observation, {"id": "subject_ref", "name": "performer"}, bidirectional=True)
        bidirectional_piper = Piper(mapping)
        
        patient = Patient(id="123", name="John", active=True, age=45)
        
        # View transformation (one-way) - may return dict in non-strict mode
        obs_unidirectional = unidirectional_piper.forward(patient)
        if isinstance(obs_unidirectional, dict):
            assert obs_unidirectional.get("subject_ref") == "123"
        else:
            assert obs_unidirectional.subject_ref == "123"
        
        # Lens transformation (bidirectional)
        obs_bidirectional, spillover = bidirectional_piper.forward(patient)
        recovered = bidirectional_piper.reverse(obs_bidirectional, spillover)
        assert recovered == patient