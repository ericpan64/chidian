"""Consolidated tests for the put function."""

from typing import Any

import pytest

from chidian import put


class TestPutBasic:
    """Test basic put operations."""

    @pytest.mark.parametrize(
        "path,value,expected",
        [
            ("simple", "value", {"simple": "value"}),
            ("nested.path", "value", {"nested": {"path": "value"}}),
            ("deep.nested.path", "value", {"deep": {"nested": {"path": "value"}}}),
        ],
    )
    def test_simple_paths(self, path: str, value: Any, expected: dict):
        """Test basic dot notation paths."""
        result = put({}, path, value)
        assert result == expected

    def test_overwrite_existing(self):
        """Test overwriting existing values."""
        data = {"a": {"b": "old"}}
        result = put(data, "a.b", "new")
        assert result == {"a": {"b": "new"}}

    def test_preserve_existing(self):
        """Test that existing data is preserved."""
        data = {"a": {"b": 1, "c": 2}}
        result = put(data, "a.d", 3)
        assert result == {"a": {"b": 1, "c": 2, "d": 3}}


class TestPutArrays:
    """Test put operations on arrays."""

    @pytest.mark.parametrize(
        "path,value,expected",
        [
            ("arr[0]", "a", {"arr": ["a"]}),
            ("arr[2]", "c", {"arr": [None, None, "c"]}),
        ],
    )
    def test_array_creation(self, path: str, value: Any, expected: dict):
        """Test creating arrays with put."""
        result = put({}, path, value)
        assert result == expected

    def test_array_gap_filling(self):
        """Test that array gaps are filled with None."""
        result = put({}, "items[5]", "value")
        assert result == {"items": [None, None, None, None, None, "value"]}
        assert len(result["items"]) == 6

    def test_nested_array_paths(self):
        """Test complex nested array paths."""
        result = put({}, "data[0].items[1].value", "test")
        expected = {"data": [{"items": [None, {"value": "test"}]}]}
        assert result == expected

    def test_negative_indices(self):
        """Test negative array indices."""
        data = {"arr": [1, 2, 3]}
        result = put(data, "arr[-1]", "changed")
        assert result == {"arr": [1, 2, "changed"]}


class TestPutEdgeCases:
    """Test edge cases and special behaviors."""

    def test_empty_path(self):
        """Test behavior with empty path."""
        with pytest.raises(ValueError):
            put({}, "", "value")

    def test_none_values(self):
        """Test putting None values."""
        result = put({}, "path", None)
        assert result == {"path": None}

    def test_complex_values(self):
        """Test putting complex values."""
        complex_value = {"nested": {"data": [1, 2, 3]}}
        result = put({}, "root", complex_value)
        assert result == {"root": complex_value}

    @pytest.mark.parametrize(
        "initial,path,value,expected",
        [
            ({"a": 1}, "b", 2, {"a": 1, "b": 2}),
            ({"a": {"b": 1}}, "a.c", 2, {"a": {"b": 1, "c": 2}}),
        ],
    )
    def test_various_updates(self, initial, path, value, expected):
        """Test various update scenarios."""
        result = put(initial, path, value)
        assert result == expected


class TestPutIntegration:
    """Test put in combination with get."""

    def test_round_trip(self):
        """Test that put and get are inverse operations."""
        from chidian import get

        paths_and_values = [
            ("a.b.c", "value1"),
            ("x.y[0].z", "value2"),
            ("arr[2].nested.field", "value3"),
        ]

        data = {}
        for path, value in paths_and_values:
            data = put(data, path, value)
            assert get(data, path) == value
