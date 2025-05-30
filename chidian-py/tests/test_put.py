from typing import Any

import pytest

from chidian.lib import put


def test_put_simple_key():
    """Test setting simple keys"""
    # Empty dict
    result = put({}, "patient", {"id": "123"})
    assert result == {"patient": {"id": "123"}}
    
    # Nested keys
    result = put({}, "patient.id", "123")
    assert result == {"patient": {"id": "123"}}
    
    # Deep nesting
    result = put({}, "patient.name.given", "John")
    assert result == {"patient": {"name": {"given": "John"}}}


def test_put_existing_structure():
    """Test setting values in existing structures"""
    # Add to existing dict
    source = {"patient": {"name": "John"}}
    result = put(source, "patient.id", "123")
    assert result == {"patient": {"name": "John", "id": "123"}}
    
    # Overwrite existing value
    source = {"patient": {"id": "123"}}
    result = put(source, "patient.id", "456")
    assert result == {"patient": {"id": "456"}}
    
    # Original should not be modified
    source = {"patient": {"id": "123"}}
    result = put(source, "patient.id", "456")
    assert source == {"patient": {"id": "123"}}  # Unchanged


def test_put_array_index():
    """Test setting values with array indices"""
    # Create array with single element
    result = put({}, "items[0]", {"value": 42})
    assert result == {"items": [{"value": 42}]}
    
    # Create array with gap
    result = put({}, "items[2]", {"value": 42})
    assert result == {"items": [None, None, {"value": 42}]}
    
    # Nested array access
    result = put({}, "items[0].value", 42)
    assert result == {"items": [{"value": 42}]}
    
    # Multiple array indices
    result = put({}, "matrix[0][1]", 42)
    assert result == {"matrix": [[None, 42]]}


def test_put_negative_index():
    """Test negative array indexing"""
    # Existing array
    source = {"items": [1, 2, 3]}
    result = put(source, "items[-1]", 4)
    assert result == {"items": [1, 2, 4]}
    
    # Out of bounds negative index (non-strict)
    source = {"items": [1, 2]}
    result = put(source, "items[-5]", 0)
    assert result == {"items": [1, 2]}  # No change
    
    # Out of bounds negative index (strict)
    source = {"items": [1, 2]}
    with pytest.raises(ValueError):
        put(source, "items[-5]", 0, strict=True)


def test_put_list_at_root():
    """Test paths that start with array index"""
    # The put function expects a dict, not a list at root
    # So we should test with a dict that has a list
    source = {"data": []}
    result = put(source, "data[0]", {"value": 42})
    assert result == {"data": [{"value": 42}]}
    
    # Test creating list from scratch
    result = put({}, "[0]", {"value": 42})
    # This creates a dict with key "[0]" since there's no parent key
    # The behavior is that we need a parent key for array indices
    assert result == {}  # Path parsing should fail for root-level brackets


def test_put_complex_paths():
    """Test complex path combinations"""
    # Mix of keys and indices
    result = put({}, "data.patients[0].medications[1].name", "Aspirin")
    expected = {
        "data": {
            "patients": [
                {
                    "medications": [
                        None,
                        {"name": "Aspirin"}
                    ]
                }
            ]
        }
    }
    assert result == expected
    
    # Multiple operations on same structure
    result = put({}, "users[0].name", "Alice")
    result = put(result, "users[0].age", 30)
    result = put(result, "users[1].name", "Bob")
    expected = {
        "users": [
            {"name": "Alice", "age": 30},
            {"name": "Bob"}
        ]
    }
    assert result == expected


def test_put_strict_mode():
    """Test strict mode error handling"""
    # Cannot traverse through non-dict
    source = {"data": "string"}
    with pytest.raises(ValueError, match="Cannot traverse into non-dict at 'data'"):
        put(source, "data.patient", "value", strict=True)
    
    # Non-strict mode returns original
    result = put(source, "data.patient", "value", strict=False)
    assert result == source
    
    # Cannot index into non-list
    source = {"items": "not a list"}
    with pytest.raises(ValueError, match="Cannot traverse into non-dict at 'items'"):
        put(source, "items[0]", "value", strict=True)
    
    # Cannot traverse into non-dict at array index
    source = {"items": ["a", "b"]}
    with pytest.raises(ValueError, match="Cannot traverse into non-dict at index"):
        put(source, "items[0].name", "value", strict=True)


def test_put_replacement_behavior():
    """Test value replacement behavior"""
    # Replace a dict with a string (non-strict)
    data = {"patient": {"id": "1", "name": "John"}}
    result = put(data, "patient", "John Doe")
    assert result == {"patient": "John Doe"}
    
    # Replace a list with a string
    data = {"items": [1, 2, 3]}
    result = put(data, "items", "replaced")
    assert result == {"items": "replaced"}
    
    # Replace a string with a dict
    data = {"status": "active"}
    result = put(data, "status", {"code": "A", "display": "Active"})
    assert result == {"status": {"code": "A", "display": "Active"}}
    
    # Deep replacement
    data = {"a": {"b": {"c": {"d": "deep"}}}}
    result = put(data, "a.b", "replaced")
    assert result == {"a": {"b": "replaced"}}
    
    # Replace in array
    data = {"items": [{"id": "1"}, {"id": "2"}]}
    result = put(data, "items[0]", "replaced")
    assert result == {"items": ["replaced", {"id": "2"}]}


def test_put_replacement_strict_mode():
    """Test replacement behavior in strict mode"""
    # In strict mode, we should allow replacement at the final segment
    data = {"patient": {"id": "1", "name": "John"}}
    
    # This should work - replacing at final path
    result = put(data, "patient", "John Doe", strict=True)
    assert result == {"patient": "John Doe"}
    
    # But traversing through non-dict should fail
    data = {"patient": "John"}
    with pytest.raises(ValueError, match="Cannot traverse into non-dict at 'patient'"):
        put(data, "patient.name", "Doe", strict=True)
    
    # Array replacement should work
    data = {"items": [1, 2, 3]}
    result = put(data, "items[1]", "replaced", strict=True)
    assert result == {"items": [1, "replaced", 3]}


def test_put_type_safety_proposal():
    """Test proposed type safety behavior for replacements"""
    # Non-strict mode: silently fail when trying to traverse through non-dict
    data = {"patient": "John"}
    result = put(data, "patient.name", "Doe", strict=False)
    assert result == {"patient": "John"}  # Unchanged
    
    # But direct replacement should work
    result = put(data, "patient", {"name": "Doe"}, strict=False)
    assert result == {"patient": {"name": "Doe"}}
    
    # Strict mode alternative: could check type compatibility
    # This is a design decision - do we want to prevent type changes in strict mode?
    # Current behavior: allows any replacement at final path
    data = {"count": 42}
    result = put(data, "count", "forty-two", strict=True)
    assert result == {"count": "forty-two"}  # Type change allowed


def test_put_edge_cases():
    """Test edge cases and special values"""
    # Set None value
    result = put({}, "value", None)
    assert result == {"value": None}
    
    # Set empty dict
    result = put({}, "value", {})
    assert result == {"value": {}}
    
    # Set empty list
    result = put({}, "value", [])
    assert result == {"value": []}
    
    # Boolean values
    result = put({}, "active", True)
    assert result == {"active": True}
    
    # Numeric values
    result = put({}, "count", 42)
    assert result == {"count": 42}
    result = put({}, "price", 19.99)
    assert result == {"price": 19.99}


def test_put_invalid_paths():
    """Test invalid path handling"""
    # Empty path
    with pytest.raises(ValueError, match="Invalid path"):
        put({}, "", "value")
    
    # Path with only dots
    with pytest.raises(ValueError, match="Invalid path"):
        put({}, "...", "value")
    
    # Invalid bracket syntax
    with pytest.raises(ValueError, match="Invalid"):
        put({}, "items[0", "value")  # Missing closing bracket
    
    
def test_put_integration_with_get():
    """Test that put and get are complementary"""
    from chidian import get
    
    # Simple case
    result = put({}, "patient.id", "123")
    assert get(result, "patient.id") == "123"
    
    # Array case
    result = put({}, "items[0].value", 42)
    assert get(result, "items[0].value") == 42
    
    # Complex nested case
    result = put({}, "data.patients[0].medications[1].name", "Aspirin")
    assert get(result, "data.patients[0].medications[1].name") == "Aspirin"
    
    # Multiple puts
    result = {}
    paths_and_values = [
        ("user.name", "Alice"),
        ("user.age", 30),
        ("user.addresses[0].city", "New York"),
        ("user.addresses[0].zip", "10001"),
        ("user.addresses[1].city", "Boston"),
        ("user.addresses[1].zip", "02101"),
    ]
    
    for path, value in paths_and_values:
        result = put(result, path, value)
    
    # Verify all values can be retrieved
    for path, expected_value in paths_and_values:
        assert get(result, path) == expected_value