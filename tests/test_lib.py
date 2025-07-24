"""Simplified integration tests for core functionality."""

from chidian import get, put


def test_get_function_basic():
    """Test basic get functionality."""
    data = {
        "patient": {
            "id": "123",
            "name": {"given": "John", "family": "Doe"},
            "contact": [
                {"system": "phone", "value": "555-1234"},
                {"system": "email", "value": "john@example.com"},
            ],
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
