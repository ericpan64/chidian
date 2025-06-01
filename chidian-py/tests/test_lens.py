"""Tests for Lens bidirectional transformations."""

import pytest
from typing import Optional
from pydantic import BaseModel

from chidian.lens import Lens
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


class TestLensBasic:
    """Test basic Lens functionality."""
    
    def test_lens_creation(self):
        """Test lens can be created with valid models and mappings."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        assert lens.source_model == Patient
        assert lens.target_model == Observation
        assert lens.mappings == {"id": "subject_ref", "name": "performer"}
        assert lens.can_reverse() is True
    
    def test_lens_invalid_models(self):
        """Test lens rejects non-Pydantic models."""
        with pytest.raises(TypeError, match="source_model must be a Pydantic v2 BaseModel"):
            Lens(dict, Observation, {"id": "subject_ref"})
        
        with pytest.raises(TypeError, match="target_model must be a Pydantic v2 BaseModel"):
            Lens(Patient, dict, {"id": "subject_ref"})
    
    def test_lens_invalid_mappings(self):
        """Test lens rejects non-string mappings."""
        with pytest.raises(TypeError, match="string path mappings"):
            Lens(Patient, Observation, {123: "subject_ref"})
        
        with pytest.raises(TypeError, match="string path mappings"):
            Lens(Patient, Observation, {"id": 456})


class TestLensForward:
    """Test forward transformations."""
    
    def test_simple_forward(self):
        """Test basic forward transformation."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = lens.forward(patient)
        
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
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        patient = Patient(
            id="123", 
            name="John", 
            active=True, 
            internal_notes="sensitive",
            age=45
        )
        obs, spillover = lens.forward(patient)
        
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        
        # All unmapped fields should be in spillover
        spillover_data = spillover._items[0]
        assert spillover_data["active"] is True
        assert spillover_data["internal_notes"] == "sensitive"
        assert spillover_data["age"] == 45
    
    def test_forward_nested_mappings(self):
        """Test forward transformation with nested path mappings."""
        lens = Lens(NestedSource, NestedTarget, {
            "patient.id": "subject_id",
            "patient.name": "subject_name",
            "metadata.created_by": "created_by"
        })
        
        source = NestedSource(
            patient={"id": "123", "name": "John", "age": 45},
            metadata={"created_by": "system", "version": "1.0"},
            extra_field="extra"
        )
        
        target, spillover = lens.forward(source)
        
        assert target.subject_id == "123"
        assert target.subject_name == "John"
        assert target.created_by == "system"
        
        # Check spillover
        spillover_data = spillover._items[0]
        assert spillover_data["patient"]["age"] == 45
        assert spillover_data["metadata"]["version"] == "1.0"
        assert spillover_data["extra_field"] == "extra"
    
    def test_forward_missing_fields(self):
        """Test forward transformation with missing source fields."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer",
            "nonexistent": "status"  # This field doesn't exist
        })
        
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = lens.forward(patient)
        
        assert obs.subject_ref == "123"
        assert obs.performer == "John"
        assert obs.status is None  # Missing field maps to None
    
    def test_forward_strict_mode(self):
        """Test forward transformation."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        # Should work with correct type
        patient = Patient(id="123", name="John", active=True)
        obs, spillover = lens.forward(patient)
        assert obs.subject_ref == "123"


class TestLensReverse:
    """Test reverse transformations."""
    
    def test_simple_reverse(self):
        """Test basic reverse transformation."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True, "age": 45}])
        
        patient = lens.reverse(obs, spillover)
        
        assert isinstance(patient, Patient)
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
        assert patient.age == 45
    
    def test_reverse_no_spillover(self):
        """Test reverse transformation with minimal spillover."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet([{"active": True}])  # Provide required field
        
        patient = lens.reverse(obs, spillover)
        
        assert patient.id == "123"
        assert patient.name == "John"
        assert patient.active is True
    
    def test_reverse_nested(self):
        """Test reverse transformation with nested mappings."""
        lens = Lens(NestedSource, NestedTarget, {
            "patient.id": "subject_id",
            "patient.name": "subject_name"
        })
        
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
        
        source = lens.reverse(target, spillover)
        
        assert source.patient["id"] == "123"
        assert source.patient["name"] == "John"
        assert source.extra_field == "extra"


class TestLensRoundtrip:
    """Test roundtrip transformations (forward + reverse)."""
    
    def test_lossless_roundtrip(self):
        """Test that forward + reverse is lossless."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        original = Patient(
            id="123", 
            name="John", 
            active=True, 
            internal_notes="sensitive",
            age=45
        )
        
        # Forward transformation
        obs, spillover = lens.forward(original)
        
        # Reverse transformation
        recovered = lens.reverse(obs, spillover)
        
        # Should be identical
        assert recovered == original
    
    def test_roundtrip_nested(self):
        """Test roundtrip with nested data (simplified)."""
        lens = Lens(NestedSource, NestedTarget, {
            "patient.id": "subject_id",
            "patient.name": "subject_name"
        })
        
        original = NestedSource(
            patient={"id": "123", "name": "John"},
            metadata={"created_by": "system", "version": "1.0"},
            extra_field="extra"
        )
        
        # Roundtrip
        target, spillover = lens.forward(original)
        recovered = lens.reverse(target, spillover)
        
        # Check key fields are preserved
        assert recovered.patient["id"] == original.patient["id"]
        assert recovered.patient["name"] == original.patient["name"]
        assert recovered.extra_field == original.extra_field


class TestLensReversibility:
    """Test lens reversibility validation."""
    
    def test_reversible_mappings(self):
        """Test that 1:1 mappings are reversible."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "performer"
        })
        
        assert lens.can_reverse() is True
    
    def test_non_reversible_mappings(self):
        """Test that many-to-one mappings are not reversible."""
        with pytest.raises(ValueError, match="not reversible.*duplicate target paths"):
            Lens(Patient, Observation, {
                "id": "subject_ref",
                "name": "subject_ref",  # Duplicate target!
                "active": "performer"
            }, strict=True)
    
    def test_non_reversible_can_reverse(self):
        """Test that can_reverse correctly identifies non-reversible mappings."""
        # Create in non-strict mode to avoid validation error
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "subject_ref",  # Duplicate target
        }, strict=False)
        
        assert lens.can_reverse() is False
    
    def test_reverse_non_reversible_fails(self):
        """Test that reverse fails on non-reversible lens."""
        lens = Lens(Patient, Observation, {
            "id": "subject_ref",
            "name": "subject_ref",  # Duplicate target
        }, strict=False)
        
        obs = Observation(subject_ref="123", performer="John")
        spillover = RecordSet()
        
        with pytest.raises(ValueError, match="cannot reverse"):
            lens.reverse(obs, spillover)