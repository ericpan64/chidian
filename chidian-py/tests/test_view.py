import pytest
from typing import Optional
from chidian.view import View

import chidian.partials as p

from pydantic import BaseModel

def test_struct_mapper_basic():
    """Test basic View functionality with Pydantic models."""

    class SourceModel(BaseModel):
        subject: dict
        effectiveDateTime: str
        valueQuantity: Optional[dict] = None
    
    class TargetModel(BaseModel):
        patient_id: str
        date: str
        value: Optional[int] = None
    
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'patient_id': 'subject.reference',
            'date': 'effectiveDateTime',
            'value': 'valueQuantity.value'
        }
    )
    
    source = SourceModel(
        subject={'reference': 'Patient/123'},
        effectiveDateTime='2024-01-01',
        valueQuantity={'value': 140, 'unit': 'mmHg'}
    )
    
    result = mapper.forward(source)
    assert isinstance(result, TargetModel)
    assert result.patient_id == 'Patient/123'
    assert result.date == '2024-01-01'
    assert result.value == 140


def test_struct_mapper_with_chains():
    """Test View with chainable functions."""

    class SourceModel(BaseModel):
        effectiveDateTime: str
        subject: dict
        code: dict
        valueQuantity: Optional[dict] = None
    
    class TargetModel(BaseModel):
        date: str
        patient_id: int
        normalized_code: str
        value: float
    
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            # Simple path
            'date': 'effectiveDateTime',
            
            # With transformation chain
            'patient_id': p.get('subject.reference') >> p.split('/') >> p.last >> p.to_int,
            
            # Multiple transforms
            'normalized_code': p.get('code.text') >> p.upper >> p.replace(' ', '_'),
            
            # With default handling
            'value': p.get('valueQuantity.value') >> p.default_to(0) >> p.to_float
        }
    )
    
    source = SourceModel(
        effectiveDateTime='2024-01-01',
        subject={'reference': 'Patient/456'},
        code={'text': 'blood pressure'},
        valueQuantity={'value': None}
    )
    
    result = mapper.forward(source)
    assert isinstance(result, TargetModel)
    assert result.date == '2024-01-01'
    assert result.patient_id == 456
    assert result.normalized_code == 'BLOOD_PRESSURE'
    assert result.value == 0.0


def test_struct_mapper_validation():
    """Test View validation with required models."""
    from chidian.view import View
    from pydantic import BaseModel
    
    class SourceModel(BaseModel):
        id: str
        name: str
    
    class TargetModel(BaseModel):
        person_id: str
        display_name: str
        required_field: str  # This is required but not mapped
    
    # Should raise error for missing required field in strict mode
    with pytest.raises(ValueError, match="Missing required target fields"):
        View(
            source_model=SourceModel,
            target_model=TargetModel,
            mapping={
                'person_id': 'id',
                'display_name': 'name'
                # missing required_field
            },
            strict=True
        )
    
    # Should work in non-strict mode
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'person_id': 'id',
            'display_name': 'name'
        },
        strict=False
    )
    
    # Validation is now internal - mapper was created successfully in non-strict mode
    assert mapper.strict is False
    assert mapper.metadata == {}


def test_struct_mapper_type_validation():
    """Test View type validation."""
    from chidian.view import View
    from pydantic import BaseModel
    
    class SourceModel(BaseModel):
        id: str
        name: str
    
    class TargetModel(BaseModel):
        person_id: str
        display_name: str
    
    # Should reject non-Pydantic classes
    with pytest.raises(TypeError, match="must be a Pydantic BaseModel"):
        View(
            source_model=dict,  # Not a Pydantic model
            target_model=TargetModel,
            mapping={'person_id': 'id'}
        )
    
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={'person_id': 'id', 'display_name': 'name'}
    )
    
    # Should validate input type in strict mode
    with pytest.raises(TypeError, match="Expected SourceModel"):
        mapper.forward({'id': '123', 'name': 'test'})  # Dict instead of model


def test_struct_mapper_with_conditionals():
    """Test View with conditional mappings."""
    from chidian.view import View
    from pydantic import BaseModel
    from typing import Optional
    
    class SourceModel(BaseModel):
        status: str
        valueQuantity: Optional[dict] = None
        valueInteger: Optional[int] = None
    
    class TargetModel(BaseModel):
        status: str
        value: Optional[float] = None
    
    # Legacy dict-based conditionals
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'status': {
                'source': 'status',
                'transform': lambda s: s.upper()
            },
            'value': {
                'source': 'valueQuantity.value',
                'condition': lambda x: 'valueQuantity' in x and x['valueQuantity'] is not None,
                'transform': lambda v: float(v) if v else 0.0
            }
        }
    )
    
    # With valueQuantity
    source1 = SourceModel(
        status='active',
        valueQuantity={'value': 140}
    )
    result1 = mapper.forward(source1)
    assert result1.status == 'ACTIVE'
    assert result1.value == 140.0
    
    # Without valueQuantity
    source2 = SourceModel(
        status='inactive',
        valueInteger=100
    )
    result2 = mapper.forward(source2)
    assert result2.status == 'INACTIVE'
    assert result2.value is None  # Condition failed


def test_struct_mapper_with_pydantic():
    """Test View with Pydantic models."""
    from chidian.view import View
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Optional
    
    class SourceModel(BaseModel):
        id: str
        name: str
        age: Optional[int] = None
        active: bool = True
    
    class TargetModel(BaseModel):
        person_id: str
        display_name: str
        age_group: str
        status: str
    
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'person_id': 'id',
            'display_name': p.get('name') >> p.upper,
            'age_group': p.get('age') >> p.ChainableFn(
                lambda age: 'adult' if age and age >= 18 else 'minor'
            ),
            'status': p.get('active') >> p.ChainableFn(
                lambda active: 'ACTIVE' if active else 'INACTIVE'
            )
        }
    )
    
    source = SourceModel(id='123', name='John Doe', age=25, active=True)
    result = mapper.forward(source)
    
    assert isinstance(result, TargetModel)
    assert result.person_id == '123'
    assert result.display_name == 'JOHN DOE'
    assert result.age_group == 'adult'
    assert result.status == 'ACTIVE'


def test_struct_mapper_with_string_mapper():
    """Test combining View with Lexicon."""
    from chidian.view import View
    from chidian.lexicon import Lexicon
    import chidian.partials as p
    from pydantic import BaseModel
    
    class SourceModel(BaseModel):
        id: str
        gender: str
        name: list[dict]
    
    class TargetModel(BaseModel):
        patient_id: str
        gender_code: str
        name: str
    
    # Code system mapper
    gender_mapper = Lexicon({
        'male': 'M',
        'female': 'F',
        'other': 'O'
    })
    
    struct_mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'patient_id': 'id',
            'gender_code': p.get('gender') >> p.ChainableFn(gender_mapper.forward),
            'name': p.get('name[0].text')
        }
    )
    
    source = SourceModel(
        id='123',
        gender='female',
        name=[{'text': 'Jane Doe'}]
    )
    
    result = struct_mapper.forward(source)
    assert result.patient_id == '123'
    assert result.gender_code == 'F'
    assert result.name == 'Jane Doe'


def test_struct_mapper_error_handling():
    """Test View error handling."""
    from chidian.view import View
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Optional
    
    class SourceModel(BaseModel):
        data: dict
    
    class TargetModel(BaseModel):
        valid: Optional[int] = None
        invalid: Optional[int] = None
        error: Optional[int] = None
    
    # Non-strict mode
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'valid': 'data.value',
            'invalid': p.get('missing.path') >> p.to_int,
            'error': p.ChainableFn(lambda x: 1 / 0)  # Will raise
        },
        strict=False
    )
    
    source = SourceModel(data={'value': 123})
    result = mapper.forward(source)
    
    # Should include valid mapping
    assert result.valid == 123
    # Should skip invalid mappings (set to None in non-strict)
    assert result.invalid is None
    assert result.error is None
    
    # Strict mode
    strict_mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={'error': p.ChainableFn(lambda x: 1 / 0)},
        strict=True
    )
    
    with pytest.raises(ValueError, match="Error mapping field 'error'"):
        strict_mapper.forward(source)


def test_struct_mapper_nested_mappings():
    """Test nested structure mappings."""
    from chidian.view import View
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Any
    
    class SourceModel(BaseModel):
        subject: dict
        code: dict
    
    class TargetModel(BaseModel):
        patient: dict
        codes: list[str]
    
    mapper = View(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={
            'patient': {
                'id': p.get('subject.reference') >> p.extract_id(),
                'display': p.get('subject.display')
            },
            'codes': p.get('code.coding') >> p.ChainableFn(
                lambda codings: [c.get('code') for c in codings] if codings else []
            )
        }
    )
    
    source = SourceModel(
        subject={
            'reference': 'Patient/789',
            'display': 'John Doe'
        },
        code={
            'coding': [
                {'system': 'LOINC', 'code': '8480-6'},
                {'system': 'SNOMED', 'code': '271649006'}
            ]
        }
    )
    
    result = mapper.forward(source)
    assert result.patient['id'] == '789'
    assert result.patient['display'] == 'John Doe'
    assert result.codes == ['8480-6', '271649006']



def test_struct_mapper_real_world():
    """Test View with realistic FHIR to OMOP mapping."""
    from chidian.view import View
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Optional, List
    
    # FHIR Observation model (simplified)
    class FHIRObservation(BaseModel):
        id: str
        status: str
        subject: dict
        effectiveDateTime: str
        code: dict
        valueQuantity: Optional[dict] = None
        component: Optional[List[dict]] = None
    
    # OMOP Measurement model (simplified)
    class OMOPMeasurement(BaseModel):
        measurement_id: int
        person_id: int
        measurement_concept_id: int
        measurement_date: str
        value_as_number: Optional[float] = None
        unit_concept_id: Optional[int] = None
        measurement_source_value: str
    
    # Concept ID mappings
    concept_mapper = {
        '8480-6': 3004249,  # Systolic BP LOINC -> OMOP
        '8462-4': 3012888,  # Diastolic BP LOINC -> OMOP
        'mmHg': 8876,       # mmHg unit -> OMOP
    }
    
    mapper = View(
        source_model=FHIRObservation,
        target_model=OMOPMeasurement,
        mapping={
            'measurement_id': p.get('id') >> p.extract_id() >> p.to_int,
            'person_id': p.get('subject.reference') >> p.extract_id() >> p.to_int,
            'measurement_concept_id': p.get('code.coding[0].code') >> p.ChainableFn(
                lambda code: concept_mapper.get(code, 0)
            ),
            'measurement_date': p.get('effectiveDateTime') >> p.split('T') >> p.first,
            'value_as_number': p.get('valueQuantity.value') >> p.to_float,
            'unit_concept_id': p.get('valueQuantity.unit') >> p.ChainableFn(
                lambda unit: concept_mapper.get(unit, 0)
            ),
            'measurement_source_value': p.get('code.coding[0].code')
        }
    )
    
    # FHIR Blood Pressure Observation
    fhir_obs = FHIRObservation(
        id='observation/12345',
        status='final',
        subject={'reference': 'Patient/789'},
        effectiveDateTime='2024-01-15T10:30:00Z',
        code={
            'coding': [
                {'system': 'http://loinc.org', 'code': '8480-6', 'display': 'Systolic BP'}
            ]
        },
        valueQuantity={
            'value': 140,
            'unit': 'mmHg',
            'system': 'http://unitsofmeasure.org'
        }
    )
    
    result = mapper.forward(fhir_obs)
    
    assert isinstance(result, OMOPMeasurement)
    assert result.measurement_id == 12345
    assert result.person_id == 789
    assert result.measurement_concept_id == 3004249  # LOINC 8480-6 -> OMOP
    assert result.measurement_date == '2024-01-15'
    assert result.value_as_number == 140.0
    assert result.unit_concept_id == 8876  # mmHg -> OMOP
    assert result.measurement_source_value == '8480-6'


def test_struct_mapper_edge_cases():
    """Test View edge cases."""
    from chidian.view import View
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Optional, List, Any
    
    class FlexibleSource(BaseModel):
        data: Optional[Any] = None
        nested: Optional[dict] = None
        arrays: Optional[List[Any]] = None
    
    class FlexibleTarget(BaseModel):
        simple: Optional[str] = None
        processed: Optional[str] = None
        count: Optional[int] = None
        safe: Optional[str] = None
    
    # Test with various edge cases
    mapper = View(
        source_model=FlexibleSource,
        target_model=FlexibleTarget,
        mapping={
            'simple': 'data',
            'processed': p.get('nested.deep.value') >> p.default_to('missing') >> p.upper,
            'count': p.get('arrays') >> p.ChainableFn(lambda arr: len(arr) if arr else 0),
            'safe': p.get('nonexistent.path') >> p.default_to('safe_default')
        },
        strict=False
    )
    
    # Test with minimal data
    source1 = FlexibleSource()
    result1 = mapper.forward(source1)
    assert result1.simple is None
    assert result1.processed == 'MISSING'
    assert result1.count == 0
    assert result1.safe == 'safe_default'
    
    # Test with full data
    source2 = FlexibleSource(
        data='test_string',
        nested={'deep': {'value': 'found'}},
        arrays=[1, 2, 3, 4, 5]
    )
    result2 = mapper.forward(source2)
    assert result2.simple == 'test_string'
    assert result2.processed == 'FOUND'
    assert result2.count == 5
    assert result2.safe == 'safe_default'  # Still uses default for missing path