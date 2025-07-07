"""Tests for Piper as independent dict->dict transformer."""

import chidian.partials as p
import pytest
from chidian import Piper, get


class TestPiperBasic:
    """Test basic Piper functionality as dict->dict transformer."""

    def test_simple_dict_mapping(self) -> None:
        """Test basic Piper with dict mapping."""
        mapping = {"patient_id": "data.patient.id", "is_active": "data.patient.active"}
        piper = Piper(mapping)

        input_data = {
            "data": {"patient": {"id": "abc123", "active": True}, "other": "value"}
        }

        result = piper(input_data)

        assert isinstance(result, dict)
        assert result["patient_id"] == "abc123"
        assert result["is_active"] is True

    def test_callable_mapping(self) -> None:
        """Test Piper with callable mapping."""

        def mapping(data: dict) -> dict:
            return {
                "patient_id": get(data, "data.patient.id"),
                "is_active": get(data, "data.patient.active"),
                "status": "processed",
            }

        piper = Piper(mapping)

        input_data = {
            "data": {"patient": {"id": "abc123", "active": True}, "other": "value"}
        }

        result = piper(input_data)

        assert isinstance(result, dict)
        assert result["patient_id"] == "abc123"
        assert result["is_active"] is True
        assert result["status"] == "processed"

    def test_callable_mapping_with_partials(self) -> None:
        """Test Piper with callable mapping using simplified partials API."""

        def mapper(data: dict) -> dict:
            # Use simplified partials API
            get_first = p.get("firstName")
            get_last = p.get("lastName")

            # Status mapping using simple approach
            status_map = {"active": "✓ Active", "inactive": "✗ Inactive"}
            status_value = get(data, "status", default="unknown")
            status_display = status_map.get(status_value, "Unknown")

            # City extraction
            city_extractor = p.get("address") >> p.split("|") >> p.at_index(1)

            # Simple name concatenation
            first_name = get_first(data) or ""
            last_name = get_last(data) or ""
            full_name = f"{first_name} {last_name}".strip()

            # Join codes
            codes = get(data, "codes", default=[])
            all_codes = ", ".join(str(c) for c in codes) if codes else ""

            # Backup name - first available value
            backup_name = get(data, "nickname") or get(data, "firstName") or "Guest"

            return {
                "name": full_name,
                "status_display": status_display,
                "all_codes": all_codes,
                "city": city_extractor(data),
                "backup_name": backup_name,
            }

        piper = Piper(mapper)

        input_data = {
            "firstName": "John",
            "lastName": "Doe",
            "status": "active",
            "codes": ["A", "B", "C"],
            "address": "123 Main St|Boston|02101",
        }

        result = piper(input_data)

        assert isinstance(result, dict)
        assert result["name"] == "John Doe"
        assert result["status_display"] == "✓ Active"
        assert result["all_codes"] == "A, B, C"
        assert result["city"] == "Boston"
        assert result["backup_name"] == "John"


class TestPiperMapping:
    """Test Piper mapping functionality."""

    def test_piper_with_invalid_mapping(self) -> None:
        """Test that Piper rejects invalid mapping types."""
        with pytest.raises(TypeError):
            Piper(123)  # type: ignore  # Invalid type

        with pytest.raises(TypeError):
            Piper("not a mapping")  # type: ignore  # Invalid type

    def test_piper_with_dict_mapping_containing_callable(self) -> None:
        """Test Piper with dict mapping containing callable values."""
        mapping = {
            "simple": "path.to.value",
            "transformed": lambda data: data.get("value", "").upper(),
            "partial": p.get("nested.value") >> p.upper,
        }
        piper = Piper(mapping)

        input_data = {
            "path": {"to": {"value": "hello"}},
            "value": "world",
            "nested": {"value": "test"},
        }

        result = piper(input_data)

        assert result["simple"] == "hello"
        assert result["transformed"] == "WORLD"
        assert result["partial"] == "TEST"

    def test_piper_error_handling(self) -> None:
        """Test Piper error handling."""

        def failing_mapper(data: dict) -> dict:  # type: ignore
            raise ValueError("Test error")

        piper = Piper(failing_mapper)

        with pytest.raises(ValueError, match="Test error"):
            piper({"test": "data"})

    def test_piper_with_empty_mapping(self) -> None:
        """Test Piper with empty mapping."""
        piper = Piper({})
        result = piper({"input": "data"})
        assert result == {}

    def test_piper_preserves_dict_structure(self) -> None:
        """Test that Piper preserves nested dict structure in results."""
        # This mapping variable is unused, but kept for documentation
        _ = {
            "flat": "simple.value",
            "nested": {"deep": "another.path", "value": "direct_value"},
        }

        def dict_mapper(data: dict) -> dict:
            return {
                "flat": get(data, "simple.value"),
                "nested": {"deep": get(data, "another.path"), "value": "direct_value"},
            }

        piper = Piper(dict_mapper)

        input_data = {"simple": {"value": "test"}, "another": {"path": "nested_test"}}

        result = piper(input_data)

        assert result["flat"] == "test"
        assert result["nested"]["deep"] == "nested_test"
        assert result["nested"]["value"] == "direct_value"


class TestPiperCalling:
    """Test Piper calling interface."""

    def test_piper_callable_interface(self) -> None:
        """Test that Piper can be called directly."""
        mapping = {"output": "input"}
        piper = Piper(mapping)

        input_data = {"input": "test_value"}
        result = piper(input_data)

        assert result["output"] == "test_value"

    def test_piper_forward_method(self) -> None:
        """Test that Piper.forward() works the same as calling."""
        mapping = {"output": "input"}
        piper = Piper(mapping)

        input_data = {"input": "test_value"}

        result1 = piper(input_data)
        result2 = piper.forward(input_data)

        assert result1 == result2

    def test_piper_no_reverse(self) -> None:
        """Test that Piper doesn't support reverse operations."""
        mapping = {"output": "input"}
        piper = Piper(mapping)

        # Should not have reverse method
        assert not hasattr(piper, "reverse")

        # Should not have can_reverse method
        assert not hasattr(piper, "can_reverse")
