import pytest
from typing import Optional
from chidian.mapper import StringMapper, Mapper


def test_basic_string_mapper():
    """Test basic one-to-one string mapping."""
    # Simple LOINC to SNOMED mapping
    mapper = StringMapper({
        '8480-6': '271649006',  # Systolic BP
        '8462-4': '271650006',  # Diastolic BP
        '2160-0': '166830008',  # Creatinine
    })
    
    # Forward mapping
    assert mapper.forward('8480-6') == '271649006'
    assert mapper.forward('8462-4') == '271650006'
    
    # Reverse mapping
    assert mapper.reverse('271649006') == '8480-6'
    assert mapper.reverse('271650006') == '8462-4'
    
    # Dict-like access (bidirectional)
    assert mapper['8480-6'] == '271649006'
    assert mapper['271649006'] == '8480-6'
    
    # Missing keys
    assert mapper.forward('unknown') is None
    assert mapper.reverse('unknown') is None


def test_many_to_one_mapping():
    """Test many-to-one mappings with default selection."""
    # Multiple status codes mapping to single value
    status_mapper = StringMapper({
        ('active', 'current', 'ongoing'): 'A',
        ('inactive', 'stopped', 'completed'): 'I',
        ('pending', 'planned'): 'P',
    })
    
    # Forward mappings - all map to same value
    assert status_mapper['active'] == 'A'
    assert status_mapper['current'] == 'A'
    assert status_mapper['ongoing'] == 'A'
    
    # Reverse mapping - returns first element by default
    assert status_mapper['A'] == 'active'  # First in tuple
    assert status_mapper['I'] == 'inactive'
    assert status_mapper['P'] == 'pending'
    
    # Test that unknown keys work with get
    assert status_mapper.get('unknown', 'DEFAULT') == 'DEFAULT'


def test_default_values():
    """Test default value handling."""
    mapper = StringMapper(
        {'yes': 'Y', 'no': 'N'},
        default='UNKNOWN'
    )
    
    # Known values
    assert mapper['yes'] == 'Y'
    assert mapper['Y'] == 'yes'
    
    # Unknown values return default
    assert mapper['maybe'] == 'UNKNOWN'
    assert mapper.forward('maybe') == 'UNKNOWN'
    assert mapper.reverse('X') == 'UNKNOWN'
    
    # get() method with custom default
    assert mapper.get('maybe', 'CUSTOM') == 'CUSTOM'


def test_metadata():
    """Test metadata storage."""
    mapper = StringMapper(
        {'401.9': 'I10'},
        metadata={
            'version': 'ICD9-to-ICD10-2023',
            'source': 'CMS',
            'assumptions': 'General equivalence mappings'
        }
    )
    
    assert mapper.metadata['version'] == 'ICD9-to-ICD10-2023'
    assert mapper.metadata['source'] == 'CMS'


def test_contains_and_len():
    """Test container protocol methods."""
    mapper = StringMapper({
        'a': '1',
        'b': '2',
        ('c', 'd'): '3'
    })
    
    # Contains checks both directions
    assert 'a' in mapper
    assert '1' in mapper
    assert 'c' in mapper
    assert 'd' in mapper
    assert '3' in mapper
    assert 'x' not in mapper
    
    # Length counts unique mappings
    assert len(mapper) == 7  # 4 forward + 3 reverse


def test_mixed_mappings():
    """Test mixing one-to-one and many-to-one mappings."""
    # Mix of direct and grouped mappings
    mapper = StringMapper({
        'red': 'R',
        'blue': 'B',
        ('green', 'emerald', 'jade'): 'G',
        'yellow': 'Y',
        ('orange', 'amber'): 'O',
    })
    
    # All forward mappings work
    assert mapper['red'] == 'R'
    assert mapper['green'] == 'G'
    assert mapper['emerald'] == 'G'
    assert mapper['jade'] == 'G'
    assert mapper['orange'] == 'O'
    
    # Reverse mappings use first element for many-to-one
    assert mapper['R'] == 'red'
    assert mapper['G'] == 'green'  # First element
    assert mapper['O'] == 'orange'  # First element


def test_empty_mapper():
    """Test empty mapper behavior."""
    mapper = StringMapper({})
    
    assert len(mapper) == 0
    assert mapper.forward('anything') is None
    assert mapper.reverse('anything') is None
    
    with pytest.raises(KeyError):
        _ = mapper['anything']


def test_dict_interface():
    """Test that StringMapper works as a dict."""
    mapper = StringMapper({'a': '1', 'b': '2'})
    
    # Dict methods should work
    assert list(mapper.keys()) == ['a', 'b']
    assert list(mapper.values()) == ['1', '2']
    assert list(mapper.items()) == [('a', '1'), ('b', '2')]
    
    # Update parent dict
    assert dict(mapper) == {'a': '1', 'b': '2'}


# StructMapper Tests
def test_struct_mapper_basic():
    """Test basic StructMapper functionality with Pydantic models."""
    from chidian.mapper import StructMapper
    from pydantic import BaseModel
    from typing import Optional
    
    class SourceModel(BaseModel):
        subject: dict
        effectiveDateTime: str
        valueQuantity: Optional[dict] = None
    
    class TargetModel(BaseModel):
        patient_id: str
        date: str
        value: Optional[int] = None
    
    mapper = StructMapper(
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
    """Test StructMapper with chainable functions."""
    from chidian.mapper import StructMapper
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Optional
    
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
    
    mapper = StructMapper(
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
    """Test StructMapper validation with required models."""
    from chidian.mapper import StructMapper
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
        StructMapper(
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
    mapper = StructMapper(
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
    """Test StructMapper type validation."""
    from chidian.mapper import StructMapper
    from pydantic import BaseModel
    
    class SourceModel(BaseModel):
        id: str
        name: str
    
    class TargetModel(BaseModel):
        person_id: str
        display_name: str
    
    # Should reject non-Pydantic classes
    with pytest.raises(TypeError, match="must be a Pydantic BaseModel"):
        StructMapper(
            source_model=dict,  # Not a Pydantic model
            target_model=TargetModel,
            mapping={'person_id': 'id'}
        )
    
    mapper = StructMapper(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={'person_id': 'id', 'display_name': 'name'}
    )
    
    # Should validate input type in strict mode
    with pytest.raises(TypeError, match="Expected SourceModel"):
        mapper.forward({'id': '123', 'name': 'test'})  # Dict instead of model


def test_struct_mapper_with_conditionals():
    """Test StructMapper with conditional mappings."""
    from chidian.mapper import StructMapper
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
    mapper = StructMapper(
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
    """Test StructMapper with Pydantic models."""
    from chidian.mapper import StructMapper
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
    
    mapper = StructMapper(
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
    """Test combining StructMapper with StringMapper."""
    from chidian.mapper import StructMapper, StringMapper
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
    gender_mapper = StringMapper({
        'male': 'M',
        'female': 'F',
        'other': 'O'
    })
    
    struct_mapper = StructMapper(
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
    """Test StructMapper error handling."""
    from chidian.mapper import StructMapper
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
    mapper = StructMapper(
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
    strict_mapper = StructMapper(
        source_model=SourceModel,
        target_model=TargetModel,
        mapping={'error': p.ChainableFn(lambda x: 1 / 0)},
        strict=True
    )
    
    with pytest.raises(ValueError, match="Error mapping field 'error'"):
        strict_mapper.forward(source)


def test_struct_mapper_nested_mappings():
    """Test nested structure mappings."""
    from chidian.mapper import StructMapper
    import chidian.partials as p
    from pydantic import BaseModel
    from typing import Any
    
    class SourceModel(BaseModel):
        subject: dict
        code: dict
    
    class TargetModel(BaseModel):
        patient: dict
        codes: list[str]
    
    mapper = StructMapper(
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


def test_mapper_protocol():
    """Test that mappers implement the Mapper protocol."""
    # StringMapper implements Mapper protocol
    string_mapper = StringMapper({'a': '1'})
    assert isinstance(string_mapper, Mapper)
    assert hasattr(string_mapper, 'forward')
    assert hasattr(string_mapper, 'metadata')
    
    # Check protocol methods work
    assert string_mapper.forward('a') == '1'
    assert isinstance(string_mapper.metadata, dict)
    
    # StringMapper has additional methods beyond the protocol
    assert hasattr(string_mapper, 'reverse')
    assert hasattr(string_mapper, 'can_reverse')
    assert string_mapper.reverse('1') == 'a'
    assert string_mapper.can_reverse() is True
    
    # StructMapper implements Mapper protocol
    from chidian.mapper import StructMapper
    from pydantic import BaseModel
    
    class Source(BaseModel):
        value: str
    
    class Target(BaseModel):
        result: str
    
    struct_mapper = StructMapper(
        source_model=Source,
        target_model=Target,
        mapping={'result': 'value'}
    )
    
    assert isinstance(struct_mapper, Mapper)
    assert hasattr(struct_mapper, 'forward')
    assert hasattr(struct_mapper, 'metadata')
    
    # Check protocol methods work
    source = Source(value='test')
    result = struct_mapper.forward(source)
    assert result.result == 'test'
    assert isinstance(struct_mapper.metadata, dict)
    
    # StructMapper has additional methods beyond the protocol
    assert hasattr(struct_mapper, 'reverse')
    assert hasattr(struct_mapper, 'can_reverse')
    assert struct_mapper.can_reverse() is False
    
    # Reverse should raise NotImplementedError
    with pytest.raises(NotImplementedError):
        struct_mapper.reverse(Target(result='test'))


def test_custom_mapper_protocol():
    """Test that custom mappers can implement the Mapper protocol."""
    # Create a minimal custom mapper that implements only the protocol requirements
    class LookupMapper:
        """Simple lookup table mapper implementing the Mapper protocol."""
        def __init__(self, lookup_table: dict):
            self.lookup = lookup_table
            self.metadata = {'type': 'lookup', 'size': len(lookup_table)}
        
        def forward(self, key: str) -> Optional[str]:
            return self.lookup.get(key)
    
    # Create instance
    mapper = LookupMapper({
        'red': '#FF0000',
        'green': '#00FF00',  
        'blue': '#0000FF'
    })
    
    # Verify it implements the protocol
    assert isinstance(mapper, Mapper)
    
    # Test protocol methods
    assert mapper.forward('red') == '#FF0000'
    assert mapper.forward('unknown') is None
    assert mapper.metadata['size'] == 3
    
    # Create a more complex mapper with additional methods
    class AdvancedLookupMapper(LookupMapper):
        """Mapper with additional functionality beyond the protocol."""
        def __init__(self, lookup_table: dict):
            super().__init__(lookup_table)
            self.reverse_lookup = {v: k for k, v in lookup_table.items()}
        
        def reverse(self, value: str) -> Optional[str]:
            return self.reverse_lookup.get(value)
        
        def can_reverse(self) -> bool:
            return len(self.lookup) == len(self.reverse_lookup)
    
    # Test the advanced mapper
    adv_mapper = AdvancedLookupMapper({
        'red': '#FF0000',
        'green': '#00FF00',
        'blue': '#0000FF'  
    })
    
    assert isinstance(adv_mapper, Mapper)
    assert adv_mapper.forward('red') == '#FF0000'
    assert adv_mapper.reverse('#00FF00') == 'green'
    assert adv_mapper.can_reverse() is True