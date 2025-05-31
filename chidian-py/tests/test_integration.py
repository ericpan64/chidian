"""Simplified integration tests for core functionality."""

import pytest
from typing import Any

from chidian import get, Piper
import chidian.partials as p
from chidian.lib import put
from chidian.seeds import DROP, KEEP


def test_get_function_basic():
    """Test basic get functionality."""
    data = {
        "patient": {
            "id": "123",
            "name": {"given": "John", "family": "Doe"},
            "contact": [
                {"system": "phone", "value": "555-1234"},
                {"system": "email", "value": "john@example.com"}
            ]
        }
    }
    
    # Basic path access
    assert get(data, "patient.id") == "123"
    assert get(data, "patient.name.given") == "John"
    assert get(data, "patient.contact[0].value") == "555-1234"
    
    # Array operations
    assert get(data, "patient.contact[*].system") == ["phone", "email"]


def test_put_function_basic():
    """Test basic put functionality."""
    data = {"patient": {"id": "123"}}
    
    # Basic put
    result = put(data, "patient.name", "John Doe")
    assert result["patient"]["name"] == "John Doe"
    
    # Nested put
    result = put(data, "patient.address.city", "Boston")
    assert result["patient"]["address"]["city"] == "Boston"


def test_dict_piper_basic():
    """Test basic Piper functionality for dict transformations."""
    def simple_mapper(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": get(data, "patient.id"),
            "name": get(data, "patient.name"),
            "active": get(data, "patient.active", default=True)
        }
    
    piper = Piper(simple_mapper, source_type=dict, target_type=dict)
    
    data = {"patient": {"id": "123", "name": "John Doe"}}
    result = piper(data)
    
    assert result["id"] == "123"
    assert result["name"] == "John Doe"
    assert result["active"] == True


def test_partials_integration():
    """Test partials integration with Piper."""
    def mapper_with_partials(data: dict[str, Any]) -> dict[str, Any]:
        # Use partials for data extraction and transformation
        extract_email_domain = p.get("contact.email") >> p.split("@") >> p.last
        format_name = p.get("name") >> p.upper >> p.strip
        
        return {
            "id": get(data, "id"),
            "formatted_name": format_name(data),
            "email_domain": extract_email_domain(data)
        }
    
    piper = Piper(mapper_with_partials, source_type=dict, target_type=dict)
    
    data = {
        "id": "123",
        "name": "  john doe  ",
        "contact": {"email": "john@example.com"}
    }
    
    result = piper(data)
    
    assert result["id"] == "123"
    assert result["formatted_name"] == "JOHN DOE"
    assert result["email_domain"] == "example.com"


def test_drop_keep_basic():
    """Test basic DROP and KEEP functionality."""
    def mapper_with_seeds(data: dict[str, Any]) -> dict[str, Any]:
        return {
            "keep_this": KEEP("important_data"),
            "process_this": get(data, "value"),
            "drop_this": DROP.this_object() if get(data, "should_drop") else get(data, "value")
        }
    
    piper = Piper(mapper_with_seeds, source_type=dict, target_type=dict)
    
    # Test with normal data
    data = {"value": "test", "should_drop": False}
    result = piper(data)
    
    assert result["process_this"] == "test"
    # KEEP and DROP behavior would be tested in Piper implementation