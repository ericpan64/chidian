"""Integration tests for core functionality."""

from chidian import getx


def test_getx_function_basic():
    """Test basic getx functionality."""
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
    assert getx(data, "patient.id") == "123"
    assert getx(data, "patient.name.given") == "John"
    assert getx(data, "patient.contact[0].value") == "555-1234"

    # Array operations
    assert getx(data, "patient.contact[*].system") == ["phone", "email"]
