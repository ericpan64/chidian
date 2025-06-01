"""Tests for DataMapping in bidirectional mode (formerly Lens)."""

import pytest
from typing import Optional
from pydantic import BaseModel

from chidian import DataMapping
from chidian.recordset import RecordSet


class Patient(BaseModel):
    """Sample Patient model for testing."""
    id: str
    name: str
    active: bool
    internal_notes: Optional[str] = None
    age: Optional[int] = None


class Observation(BaseModel):
    """Sample Observation model for testing."""
    subject_ref: str
    performer: str
    status: Optional[str] = None


class NestedSource(BaseModel):
    """Model with nested structure."""
    patient: dict
    metadata: dict
    extra_field: Optional[str] = None


class NestedTarget(BaseModel):
    """Target with different nesting."""
    subject_id: str
    subject_name: str
    created_by: Optional[str] = None


class TestDataMappingBidirectionalBasic:
    """Test basic Lens functionality."""
    
    def test_mapping_creation(self):
        """Test mapping can be created with valid models and mappings."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        assert mapping.source_model == Patient
        assert mapping.target_model == Observation
        assert mapping.mapping == {"id": "subject_ref", "name": "performer"}
        assert mapping.can_reverse() is True
    
    def test_mapping_invalid_models(self):
        """Test mapping rejects non-Pydantic models."""
        with pytest.raises(TypeError, match="source_model must be a Pydantic v2 BaseModel"):
            DataMapping(dict, Observation, mapping={"id": "subject_ref"}, bidirectional=True)
        
        with pytest.raises(TypeError, match="target_model must be a Pydantic v2 BaseModel"):
            DataMapping(Patient, dict, mapping={"id": "subject_ref"}, bidirectional=True)
    
    def test_mapping_invalid_mappings(self):
        """Test mapping rejects non-string mappings."""
        with pytest.raises(TypeError, match="Bidirectional mappings must be string-to-string paths"):
            DataMapping(Patient, Observation, mapping={123: "subject_ref"}, bidirectional=True)
        
        with pytest.raises(TypeError, match="Bidirectional mappings must be string-to-string paths"):
            DataMapping(Patient, Observation, mapping={"id": 456}, bidirectional=True)


class TestDataMappingBidirectionalForward:
    """Test forward transformations."""
    
    def test_simple_forward(self):
        """Test basic forward transformation."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = mapping.forward(patient)
        
        assert isinstance(obs, Observation)
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        assert obs.status is None
        
        # Check spillover contains unmapped fields
        assert len(spillover) == 1
        spillover_data = spillover._items[0]
        assert spillover_data["active"] is True
    
    def test_forward_with_spillover(self):
        """Test forward transformation with multiple spillover fields."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        patient = Patient(
            id="123", 
            name="John", 
            active=True, 
            internal_notes="sensitive",
            age=45
        )
        obs, spillover = mapping.forward(patient)
        
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        
        # All unmapped fields should be in spillover
        spillover_data = spillover._items[0]
        assert spillover_data["active"] is True
        assert spillover_data["internal_notes"] == "sensitive"
        assert spillover_data["age"] == 45
    
    def test_forward_nested_mappings(self):
        """Test forward transformation with nested path mappings."""
        mapping = DataMapping(NestedSource, NestedTarget, mapping={
            "patient.id": "subject_id",
            "patient.name": "subject_name",
            "metadata.created_by": "created_by"
        }, bidirectional=True)
        
        source = NestedSource(
            patient={"id": "123", "name": "John", "age": 45},
            metadata={"created_by": "system", "version": "1.0"},
            extra_field="extra"
        )
        
        target, spillover = mapping.forward(source)
        
        assert target.subject_id == "123"
        assert target.subject_name == "John"
        assert target.created_by == "system"
        
        # Check spillover
        spillover_data = spillover._items[0]
        # The unmapped patient.age should be in spillover
        assert "patient" in spillover_data
        assert spillover_data["patient"]["age"] == 45
        # The unmapped metadata.version should be in spillover
        assert "metadata" in spillover_data
        assert spillover_data["metadata"]["version"] == "1.0"
        # The completely unmapped field should be in spillover
        assert spillover_data["extra_field"] == "extra"
    
    def test_forward_missing_fields(self):
        """Test forward transformation with missing source fields."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer",
            "nonexistent": "status"  # This field doesn't exist
        }, bidirectional=True)
        
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = mapping.forward(patient)
        
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        assert obs.status is None  # Missing field maps to None
    
    def test_forward_strict_mode(self):
        """Test forward transformation."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        # Should work with correct type
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = mapping.forward(patient)
        assert obs.subject_ref == "123"


class TestDataMappingBidirectionalReverse:
    """Test reverse transformations."""
    
    def test_simple_reverse(self):
        """Test basic reverse transformation."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True, "age": 45}])
        
        patient = mapping.reverse(obs, spillover)
        
        assert isinstance(patient, Patient)
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
        assert patient.age == 45
    
    def test_reverse_no_spillover(self):
        """Test reverse transformation with minimal spillover."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True}])  # Provide required field
        
        patient = mapping.reverse(obs, spillover)
        
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
    
    def test_reverse_nested(self):
        """Test reverse transformation with nested mappings."""
        mapping = DataMapping(NestedSource, NestedTarget, mapping={
            "patient.id": "subject_id",
            "patient.name": "subject_name"
        }, bidirectional=True)
        
        target = NestedTarget(
            subject_id="123",
            subject_name="John", 
            created_by="system"
        )
        spillover = RecordSet([{
            "patient": {"age": 45},
            "metadata": {"created_by": "system", "version": "1.0"},
            "extra_field": "extra"
        }])
        
        source = mapping.reverse(target, spillover)
        
        assert source.patient["id"] == "123"
        assert source.patient["name"] == "John"
        assert source.extra_field == "extra"


class TestDataMappingBidirectionalRoundtrip:
    """Test roundtrip transformations (forward + reverse)."""
    
    def test_lossless_roundtrip(self):
        """Test that forward + reverse is lossless."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        original = Patient(
            id="123", 
            name="John", 
            active=True, 
            internal_notes="sensitive",
            age=45
        )
        
        # Forward transformation
        obs, spillover = mapping.forward(original)
        
        # Reverse transformation
        recovered = mapping.reverse(obs, spillover)
        
        # Should be identical
        assert recovered == original
    
    def test_roundtrip_nested(self):
        """Test roundtrip with nested data (simplified)."""
        mapping = DataMapping(NestedSource, NestedTarget, mapping={
            "patient.id": "subject_id",
            "patient.name": "subject_name"
        }, bidirectional=True)
        
        original = NestedSource(
            patient={"id": "123", "name": "John"},
            metadata={"created_by": "system", "version": "1.0"},
            extra_field="extra"
        )
        
        # Roundtrip
        target, spillover = mapping.forward(original)
        recovered = mapping.reverse(target, spillover)
        
        # Check key fields are preserved
        assert recovered.patient["id"] == original.patient["id"]
        assert recovered.patient["name"] == original.patient["name"]
        assert recovered.extra_field == original.extra_field


class TestDataMappingBidirectionalReversibility:
    """Test mapping reversibility validation."""
    
    def test_reversible_mappings(self):
        """Test that 1:1 mappings are reversible."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "performer"
        }, bidirectional=True)
        
        assert mapping.can_reverse() is True
    
    def test_non_reversible_mappings(self):
        """Test that many-to-one mappings are not reversible."""
        with pytest.raises(ValueError, match="not reversible.*duplicate target paths"):
            DataMapping(Patient, Observation, mapping={
                "id": "subject_ref",
                "name": "subject_ref",  # Duplicate target!
                "active": "performer"
            }, strict=True, bidirectional=True)
    
    def test_non_reversible_can_reverse(self):
        """Test that can_reverse correctly identifies non-reversible mappings."""
        # Create in non-strict mode to avoid validation error
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "subject_ref",  # Duplicate target
        }, strict=False, bidirectional=True)
        
        assert mapping.can_reverse() is False
    
    def test_reverse_non_reversible_fails(self):
        """Test that reverse fails on non-reversible mapping."""
        mapping = DataMapping(Patient, Observation, mapping={
            "id": "subject_ref",
            "name": "subject_ref",  # Duplicate target
        }, strict=False, bidirectional=True)
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet()
        
        with pytest.raises(ValueError, match="cannot reverse"):
            mapping.reverse(obs, spillover)