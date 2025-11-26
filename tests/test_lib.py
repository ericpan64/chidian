"""Integration tests for core functionality."""

from chidian import grab


def test_grab_function_basic():
    """Test basic grab functionality."""
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
    assert grab(data, "patient.id") == "123"
    assert grab(data, "patient.name.given") == "John"
    assert grab(data, "patient.contact[0].value") == "555-1234"

    # Array operations
    assert grab(data, "patient.contact[*].system") == ["phone", "email"]
