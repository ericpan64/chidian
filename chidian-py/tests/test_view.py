"""Consolidated tests for the View class."""

import pytest
from pydantic import BaseModel
from typing import Optional, List
from chidian.view import View
import chidian.partials as p


class TestViewBasic:
    """Test basic View functionality."""
    
    def test_simple_mapping(self):
        """Test basic field mapping with Pydantic models."""
        class Source(BaseModel):
            id: str
            name: str
            
        class Target(BaseModel):
            person_id: str
            display_name: str
            
        view = View(
            source_model=Source,
            target_model=Target,
            mapping={
                'person_id': 'id',
                'display_name': 'name'
            }
        )
        
        source = Source(id='123', name='John Doe')
        result = view.forward(source)
        
        assert isinstance(result, Target)
        assert result.person_id == '123'
        assert result.display_name == 'John Doe'
        
    def test_nested_paths(self):
        """Test mapping with nested paths."""
        class Source(BaseModel):
            subject: dict
            valueQuantity: dict
            
        class Target(BaseModel):
            patient_id: str
            value: float
            
        view = View(
            source_model=Source,
            target_model=Target,
            mapping={
                'patient_id': 'subject.reference',
                'value': 'valueQuantity.value'
            }
        )
        
        source = Source(
            subject={'reference': 'Patient/123'},
            valueQuantity={'value': 140.0, 'unit': 'mmHg'}
        )
        result = view.forward(source)
        
        assert result.patient_id == 'Patient/123'
        assert result.value == 140.0
        
    def test_with_transformations(self):
        """Test mapping with chainable transformations."""
        class Source(BaseModel):
            name: str
            reference: str
            
        class Target(BaseModel):
            name_upper: str
            id: int
            
        view = View(
            source_model=Source,
            target_model=Target,
            mapping={
                'name_upper': p.get('name') >> p.upper,
                'id': p.get('reference') >> p.split('/') >> p.last >> p.to_int
            }
        )
        
        source = Source(name='john doe', reference='Patient/456')
        result = view.forward(source)
        
        assert result.name_upper == 'JOHN DOE'
        assert result.id == 456


class TestViewValidation:
    """Test View validation and error handling."""
    
    def test_strict_mode_validation(self):
        """Test strict mode enforces required fields."""
        class Source(BaseModel):
            id: str
            
        class Target(BaseModel):
            id: str
            required_field: str  # Required but not mapped
            
        # Should raise in strict mode
        with pytest.raises(ValueError, match="Missing required target fields"):
            View(
                source_model=Source,
                target_model=Target,
                mapping={'id': 'id'},
                strict=True
            )
            
        # Should work in non-strict mode
        view = View(
            source_model=Source,
            target_model=Target,
            mapping={'id': 'id'},
            strict=False
        )
        assert view.strict is False
        
    def test_type_validation(self):
        """Test that non-Pydantic models are rejected."""
        with pytest.raises(TypeError, match="must be a Pydantic BaseModel"):
            View(
                source_model=dict,  # Not a Pydantic model
                target_model=BaseModel,
                mapping={}
            )
            
    def test_error_handling(self):
        """Test error handling in mappings."""
        class Source(BaseModel):
            data: dict
            
        class Target(BaseModel):
            safe: Optional[str] = None
            error: Optional[str] = None
            
        # Non-strict mode handles errors gracefully
        view = View(
            source_model=Source,
            target_model=Target,
            mapping={
                'safe': 'data.value',
                'error': p.ChainableFn(lambda x: 1/0)  # Will raise
            },
            strict=False
        )
        
        source = Source(data={'value': 'test'})
        result = view.forward(source)
        
        assert result.safe == 'test'
        assert result.error is None  # Error was caught


class TestViewRealWorld:
    """Test real-world transformation scenarios."""
    
    def test_fhir_to_flat_structure(self, fhir_observation):
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
            
        view = View(
            source_model=FHIRObservation,
            target_model=FlatObservation,
            mapping={
                'observation_id': 'id',
                'patient_id': p.get('subject.reference') >> p.split('/') >> p.last,
                'loinc_code': 'code.coding[0].code',
                'value': 'valueQuantity.value',
                'unit': 'valueQuantity.unit'
            }
        )
        
        source = FHIRObservation(**fhir_observation)
        result = view.forward(source)
        
        assert result.observation_id == 'obs-123'
        assert result.patient_id == '456'
        assert result.loinc_code == '8480-6'
        assert result.value == 140.0
        assert result.unit == 'mmHg'