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


def test_string_mapper_protocol():
    """Test that StringMapper implements the Mapper protocol."""
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


def test_string_mapper_real_world():
    """Test StringMapper with realistic healthcare code mappings."""
    
    # LOINC to SNOMED CT mapping for common lab tests
    lab_mapper = StringMapper({
        # Blood pressure codes
        '8480-6': '271649006',  # Systolic blood pressure
        '8462-4': '271650006',  # Diastolic blood pressure
        
        # Lipid panel
        '2093-3': '166830008',  # Total cholesterol
        '2085-9': '166847007',  # HDL cholesterol
        '2089-1': '166853002',  # LDL cholesterol
        
        # Basic metabolic panel
        ('2160-0', '38483-4'): '113075003',  # Creatinine (multiple LOINC codes)
        '2951-2': '88480006',   # Sodium
        '2823-3': '88480006',   # Potassium
    }, metadata={
        'version': '2023-Q4',
        'source': 'LOINC-SNOMED-CT-Mapping',
        'purpose': 'Lab result standardization'
    })
    
    # Test forward mappings
    assert lab_mapper.forward('8480-6') == '271649006'
    assert lab_mapper.forward('2160-0') == '113075003'  # Many-to-one
    assert lab_mapper.forward('38483-4') == '113075003'  # Many-to-one
    
    # Test reverse mappings
    assert lab_mapper.reverse('271649006') == '8480-6'
    assert lab_mapper.reverse('113075003') == '2160-0'  # First in tuple
    
    # Test bidirectional access
    assert lab_mapper['2093-3'] == '166830008'
    assert lab_mapper['166830008'] == '2093-3'
    
    # Test metadata
    assert lab_mapper.metadata['version'] == '2023-Q4'
    assert lab_mapper.can_reverse() is True
    
    
def test_string_mapper_edge_cases():
    """Test StringMapper edge cases and error handling."""
    
    # Empty string mappings
    mapper = StringMapper({
        '': 'empty_key',
        'empty_value': '',
        'normal': 'value'
    })
    
    assert mapper[''] == 'empty_key'
    assert mapper['empty_value'] == ''
    assert mapper['empty_key'] == ''
    assert mapper[''] == 'empty_key'
    
    # Special characters and unicode
    unicode_mapper = StringMapper({
        'café': 'coffee',
        '你好': 'hello',
        '🏥': 'hospital',
        'test-with-dash': 'dashed',
        'test.with.dots': 'dotted'
    })
    
    assert unicode_mapper['café'] == 'coffee'
    assert unicode_mapper['你好'] == 'hello'
    assert unicode_mapper['🏥'] == 'hospital'
    assert unicode_mapper['coffee'] == 'café'
    
    # Large mappings
    large_mapper = StringMapper({
        f'key_{i}': f'value_{i}' 
        for i in range(1000)
    })
    
    assert len(large_mapper) == 2000  # 1000 forward + 1000 reverse
    assert large_mapper['key_500'] == 'value_500'
    assert large_mapper['value_500'] == 'key_500'


def test_string_mapper_conflicts():
    """Test StringMapper behavior with potential conflicts."""
    
    # Test overlapping mappings (should work fine)
    mapper = StringMapper({
        'A': '1',
        'B': '2',
        ('C', 'D'): '3',
        'E': '1',  # Same target as 'A' - this will create reverse conflict
    })
    
    # Forward mappings should all work
    assert mapper['A'] == '1'
    assert mapper['E'] == '1'
    assert mapper['C'] == '3'
    assert mapper['D'] == '3'
    
    # Reverse mapping for '1' will be the last one processed (E)
    # This is implementation dependent, but both A and E map to '1'
    reverse_result = mapper.reverse('1')
    assert reverse_result in ['A', 'E']  # Either is acceptable
    
    # Test case sensitivity
    case_mapper = StringMapper({
        'Hello': 'greeting',
        'HELLO': 'loud_greeting',
        'hello': 'quiet_greeting'
    })
    
    assert case_mapper['Hello'] == 'greeting'
    assert case_mapper['HELLO'] == 'loud_greeting'
    assert case_mapper['hello'] == 'quiet_greeting'
    
    # Each should reverse correctly
    assert case_mapper['greeting'] == 'Hello'
    assert case_mapper['loud_greeting'] == 'HELLO'
    assert case_mapper['quiet_greeting'] == 'hello'