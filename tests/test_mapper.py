"""Tests for Mapper as independent dict->dict transformer and DataMapping executor."""

from typing import Any

import pytest
from pydantic import BaseModel

import chidian.partials as p
from chidian import DataMapping, Mapper, MapperResult, ValidationMode, get


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
        assert result["patient_id"] == "abc123"  # type: ignore[index]
        assert result["is_active"] is True  # type: ignore[index]

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
        assert result["patient_id"] == "abc123"  # type: ignore[index]
        assert result["is_active"] is True  # type: ignore[index]
        assert result["status"] == "processed"  # type: ignore[index]

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
            "city": p.get("address") | p.split("|") | p.at_index(1),
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
        assert result["name"] == "John Doe"  # type: ignore[index]
        assert result["status_display"] == "✓ Active"  # type: ignore[index]
        assert result["all_codes"] == "A, B, C"  # type: ignore[index]
        assert result["city"] == "Boston"  # type: ignore[index]
        assert result["backup_name"] == "John"  # type: ignore[index]


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
            "partial": p.get("nested.value") | p.upper,
        }
        mapper = Mapper(mapping)

        input_data = {
            "path": {"to": {"value": "hello"}},
            "value": "world",
            "nested": {"value": "test"},
        }

        result = mapper(input_data)

        assert result["simple"] == "hello"  # type: ignore[index]
        assert result["transformed"] == "WORLD"  # type: ignore[index]
        assert result["partial"] == "TEST"  # type: ignore[index]

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

        assert result["constant_string"] == "Hello, World!"  # type: ignore[index]
        assert result["constant_number"] == 42  # type: ignore[index]
        assert result["constant_bool"] is True  # type: ignore[index]
        assert result["constant_none"] is None  # type: ignore[index]
        assert result["dynamic_value"] == "dynamic"  # type: ignore[index]

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

        assert result["flat"] == "test"  # type: ignore[index]
        assert result["nested"]["deep"] == "nested_test"  # type: ignore[index]
        assert result["nested"]["value"] == "direct_value"  # type: ignore[index]


class TestMapperCalling:
    """Test Mapper calling interface."""

    def test_mapper_callable_interface(self) -> None:
        """Test that Mapper can be called directly."""
        mapping = {"output": p.get("input")}
        mapper = Mapper(mapping)

        input_data = {"input": "test_value"}
        result = mapper(input_data)

        assert result["output"] == "test_value"  # type: ignore[index]

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


class TestMapperWithDataMapping:
    """Test new Mapper functionality with DataMapping."""

    def test_mapper_backward_compatibility(self) -> None:
        """Test that Mapper maintains backward compatibility with dict."""
        # Old-style dict mapping should still work
        mapper = Mapper({"output": p.get("input")})
        result = mapper({"input": "test"})
        assert result == {"output": "test"}

    def test_mapper_with_data_mapping_strict(self) -> None:
        """Test Mapper with DataMapping in strict mode."""

        class InputModel(BaseModel):
            name: str
            age: int

        class OutputModel(BaseModel):
            display_name: str
            age_group: str

        data_mapping = DataMapping(
            transformations={
                "display_name": p.get("name") | p.upper,
                "age_group": lambda d: "adult" if d.get("age", 0) >= 18 else "child",
            },
            input_schema=InputModel,
            output_schema=OutputModel,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.STRICT)

        # Valid input
        result = mapper({"name": "John", "age": 25})
        assert isinstance(result, OutputModel)
        assert result.display_name == "JOHN"
        assert result.age_group == "adult"

        # Invalid input should raise
        with pytest.raises(Exception):
            mapper({"name": "John"})  # Missing age

    def test_mapper_with_data_mapping_flexible(self) -> None:
        """Test Mapper with DataMapping in flexible mode."""

        class InputModel(BaseModel):
            name: str
            age: int

        class OutputModel(BaseModel):
            display_name: str
            age_group: str

        data_mapping = DataMapping(
            transformations={
                "display_name": p.get("name") | p.upper,
                "age_group": lambda d: "adult" if d.get("age", 0) >= 18 else "child",
            },
            input_schema=InputModel,
            output_schema=OutputModel,
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)

        # Valid input
        result = mapper({"name": "John", "age": 25})
        assert isinstance(result, MapperResult)
        assert not result.has_issues
        assert result.data.display_name == "JOHN"

        # Invalid input should return issues
        result = mapper({"name": "John"})  # Missing age
        assert isinstance(result, MapperResult)
        assert result.has_issues
        assert any(issue.field == "age" for issue in result.issues)

    def test_mapper_auto_mode(self) -> None:
        """Test Mapper auto mode selection."""
        # With schemas -> strict
        data_mapping_with_schemas = DataMapping(
            transformations={"out": p.get("in")},
            input_schema=BaseModel,
            output_schema=BaseModel,
        )
        mapper = Mapper(data_mapping_with_schemas)
        assert mapper.mode == ValidationMode.STRICT

        # Without schemas -> flexible
        data_mapping_no_schemas = DataMapping(transformations={"out": p.get("in")})
        mapper = Mapper(data_mapping_no_schemas)
        assert mapper.mode == ValidationMode.FLEXIBLE

    def test_mapper_with_pure_data_mapping(self) -> None:
        """Test Mapper with DataMapping without schemas."""
        data_mapping = DataMapping(
            transformations={
                "id": p.get("patient.id"),
                "name": p.get("patient.name"),
                "provider": p.get("provider.name", default="Unknown"),
            }
        )

        mapper = Mapper(data_mapping, mode=ValidationMode.FLEXIBLE)

        result = mapper(
            {
                "patient": {"id": "123", "name": "John"},
                "provider": {"name": "Dr. Smith"},
            }
        )

        assert isinstance(result, MapperResult)
        assert result.data["id"] == "123"
        assert result.data["name"] == "John"
        assert result.data["provider"] == "Dr. Smith"
