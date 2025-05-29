import pytest
from chidian.mapper import StringMapper


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
    
    # Check conflicts are detected
    conflicts = status_mapper.get_conflicts()
    assert 'A' in conflicts
    assert set(conflicts['A']) == {'active', 'current', 'ongoing'}


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