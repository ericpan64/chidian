"""Tests for Mapper as independent dict->dict transformer."""

from typing import Any

import pytest

import chidian.partials as p
from chidian import Mapper, get


class TestMapperBasic:
    """Test basic Mapper functionality as dict->dict transformer."""

    def test_simple_dict_mapping(self) -> None:
        """Test basic Mapper with dict mapping."""
        mapping = {
            "patient_id": p.get("data.patient.id"),
            "is_active": p.get("data.patient.active"),
        }
        mapper = Mapper(mapping)

        input_data = {
            "data": {"patient": {"id": "abc123", "active": True}, "other": "value"}
        }

        result = mapper(input_data)

        assert isinstance(result, dict)
        assert result["patient_id"] == "abc123"
        assert result["is_active"] is True

    def test_callable_mapping(self) -> None:
        """Test Mapper with callable mapping values."""
        mapping = {
            "patient_id": lambda data: get(data, "data.patient.id"),
            "is_active": lambda data: get(data, "data.patient.active"),
            "status": lambda data: "processed",
        }

        mapper = Mapper(mapping)

        input_data = {
            "data": {"patient": {"id": "abc123", "active": True}, "other": "value"}
        }

        result = mapper(input_data)

        assert isinstance(result, dict)
        assert result["patient_id"] == "abc123"
        assert result["is_active"] is True
        assert result["status"] == "processed"

    def test_callable_mapping_with_partials(self) -> None:
        """Test Mapper with callable mapping values using simplified partials API."""
        # Use simplified partials API
        get_first = p.get("firstName")
        get_last = p.get("lastName")

        # Status mapping function
        def status_transform(data: dict) -> str:
            status_map = {"active": "✓ Active", "inactive": "✗ Inactive"}
            status_value = get(data, "status", default="unknown")
            return status_map.get(status_value, "Unknown")

        # Name concatenation function
        def full_name_transform(data: dict) -> str:
            first_name = get_first(data) or ""
            last_name = get_last(data) or ""
            return f"{first_name} {last_name}".strip()

        # Codes joining function
        def codes_transform(data: dict) -> str:
            codes = get(data, "codes", default=[])
            return ", ".join(str(c) for c in codes) if codes else ""

        # Backup name function
        def backup_name_transform(data: dict) -> str:
            return get(data, "nickname") or get(data, "firstName") or "Guest"

        mapping = {
            "name": full_name_transform,
            "status_display": status_transform,
            "all_codes": codes_transform,
            "city": p.get("address") >> p.split("|") >> p.at_index(1),
            "backup_name": backup_name_transform,
        }

        mapper = Mapper(mapping)

        input_data = {
            "firstName": "John",
            "lastName": "Doe",
            "status": "active",
            "codes": ["A", "B", "C"],
            "address": "123 Main St|Boston|02101",
        }

        result = mapper(input_data)

        assert isinstance(result, dict)
        assert result["name"] == "John Doe"
        assert result["status_display"] == "✓ Active"
        assert result["all_codes"] == "A, B, C"
        assert result["city"] == "Boston"
        assert result["backup_name"] == "John"


class TestMapperMapping:
    """Test Mapper mapping functionality."""

    def test_mapper_with_invalid_mapping(self) -> None:
        """Test that Mapper rejects invalid mapping types."""
        with pytest.raises(TypeError):
            Mapper(123)  # type: ignore  # Invalid type

        with pytest.raises(TypeError):
            Mapper("not a mapping")  # type: ignore  # Invalid type

        with pytest.raises(TypeError):
            Mapper(lambda x: x)  # type: ignore  # Callable not allowed

    def test_mapper_with_dict_mapping_containing_callable(self) -> None:
        """Test Mapper with dict mapping containing callable values."""
        mapping = {
            "simple": p.get("path.to.value"),
            "transformed": lambda data: data.get("value", "").upper(),
            "partial": p.get("nested.value") >> p.upper,
        }
        mapper = Mapper(mapping)

        input_data = {
            "path": {"to": {"value": "hello"}},
            "value": "world",
            "nested": {"value": "test"},
        }

        result = mapper(input_data)

        assert result["simple"] == "hello"
        assert result["transformed"] == "WORLD"
        assert result["partial"] == "TEST"

    def test_mapper_error_handling(self) -> None:
        """Test Mapper error handling."""

        def failing_mapper(data: dict) -> str:
            raise ValueError("Test error")

        mapping: dict[str, Any] = {"result": failing_mapper}
        mapper = Mapper(mapping)

        with pytest.raises(ValueError, match="Test error"):
            mapper({"test": "data"})

    def test_mapper_with_empty_mapping(self) -> None:
        """Test Mapper with empty mapping."""
        mapper = Mapper({})
        result = mapper({"input": "data"})
        assert result == {}

    def test_mapper_with_constant_values(self) -> None:
        """Test Mapper with constant string and other values."""
        mapping = {
            "constant_string": "Hello, World!",
            "constant_number": 42,
            "constant_bool": True,
            "constant_none": None,
            "dynamic_value": p.get("input.value"),
        }
        mapper = Mapper(mapping)

        input_data = {"input": {"value": "dynamic"}, "ignored": "data"}
        result = mapper(input_data)

        assert result["constant_string"] == "Hello, World!"
        assert result["constant_number"] == 42
        assert result["constant_bool"] is True
        assert result["constant_none"] is None
        assert result["dynamic_value"] == "dynamic"

    def test_mapper_preserves_dict_structure(self) -> None:
        """Test that Mapper preserves nested dict structure in results."""
        # Note: Mapper only supports flat dictionaries, not nested output structures
        # To achieve nested results, use callables that return nested dicts

        def nested_transform(data: dict) -> dict:
            return {"deep": get(data, "another.path"), "value": "direct_value"}

        mapping = {
            "flat": p.get("simple.value"),
            "nested": nested_transform,
        }

        mapper = Mapper(mapping)

        input_data = {"simple": {"value": "test"}, "another": {"path": "nested_test"}}

        result = mapper(input_data)

        assert result["flat"] == "test"
        assert result["nested"]["deep"] == "nested_test"
        assert result["nested"]["value"] == "direct_value"


class TestMapperCalling:
    """Test Mapper calling interface."""

    def test_mapper_callable_interface(self) -> None:
        """Test that Mapper can be called directly."""
        mapping = {"output": p.get("input")}
        mapper = Mapper(mapping)

        input_data = {"input": "test_value"}
        result = mapper(input_data)

        assert result["output"] == "test_value"

    def test_mapper_callable_only(self) -> None:
        """Test that Mapper only has __call__ method (no forward method)."""
        mapping = {"output": p.get("input")}
        mapper = Mapper(mapping)

        input_data = {"input": "test_value"}

        # Should work with __call__
        result = mapper(input_data)
        assert result == {"output": "test_value"}

        # Should not have forward method
        assert not hasattr(mapper, "forward")

    def test_mapper_no_reverse(self) -> None:
        """Test that Mapper doesn't support reverse operations."""
        mapping = {"output": p.get("input")}
        mapper = Mapper(mapping)

        # Should not have reverse method
        assert not hasattr(mapper, "reverse")

        # Should not have can_reverse method
        assert not hasattr(mapper, "can_reverse")
