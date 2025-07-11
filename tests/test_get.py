"""Consolidated tests for the get function."""

from typing import Any

import pytest

from chidian import get


class TestGetBasic:
    """Test basic get operations."""

    @pytest.mark.parametrize(
        "path,expected_key",
        [
            ("data", "data"),
            ("data.patient.id", ["data", "patient", "id"]),
            ("data.patient.active", ["data", "patient", "active"]),
        ],
    )
    def test_simple_paths(self, simple_data: dict[str, Any], path: str, expected_key):
        """Test basic dot notation paths."""
        result = get(simple_data, path)

        # Navigate to expected value
        expected = simple_data
        if isinstance(expected_key, list):
            for key in expected_key:
                expected = expected[key]
        else:
            expected = expected[expected_key]

        assert result == expected

    def test_missing_paths(self, simple_data: dict[str, Any]):
        """Test behavior with missing paths."""
        assert get(simple_data, "missing") is None
        assert get(simple_data, "data.missing") is None
        assert get(simple_data, "missing", default="DEFAULT") == "DEFAULT"

    def test_apply_function(self, simple_data: dict[str, Any]):
        """Test applying transformation functions."""
        result = get(simple_data, "data.patient.id", apply=lambda x: x + "_modified")
        assert result == simple_data["data"]["patient"]["id"] + "_modified"


class TestGetArrays:
    """Test get operations on arrays."""

    @pytest.mark.parametrize(
        "path,indices",
        [
            ("list_data[0].patient", [0]),
            ("list_data[1].patient", [1]),
            ("list_data[-1].patient", [-1]),
        ],
    )
    def test_single_index(
        self, simple_data: dict[str, Any], path: str, indices: list[int]
    ):
        """Test single array index access."""
        result = get(simple_data, path)
        expected = simple_data["list_data"][indices[0]]["patient"]
        assert result == expected

    def test_out_of_bounds_index(self, simple_data: dict[str, Any]):
        """Test behavior with out of bounds indices."""
        assert get(simple_data, "list_data[5000].patient") is None

    @pytest.mark.parametrize(
        "path,slice_params",
        [
            ("list_data[1:3]", (1, 3)),
            ("list_data[1:]", (1, None)),
            ("list_data[:2]", (None, 2)),
            ("list_data[:]", (None, None)),
        ],
    )
    def test_array_slicing(self, simple_data: dict[str, Any], path: str, slice_params):
        """Test array slicing operations."""
        result = get(simple_data, path)
        start, stop = slice_params
        expected = simple_data["list_data"][start:stop]
        assert result == expected

    def test_slice_then_access(self, simple_data: dict[str, Any]):
        """Test slicing followed by property access."""
        result = get(simple_data, "list_data[1:3].patient")
        expected = [item["patient"] for item in simple_data["list_data"][1:3]]
        assert result == expected

    def test_wildcard_on_list(self, list_data: list[Any]):
        """Test wildcard operations on lists."""
        assert get(list_data, "[*].patient") == [p["patient"] for p in list_data]
        assert get(list_data, "[:].patient.id") == [
            p["patient"]["id"] for p in list_data
        ]


class TestGetEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.parametrize(
        "data,path,expected",
        [
            ({}, "any.path", None),
            (None, "any.path", None),
            ({"a": None}, "a", None),
            ({"a": {"b": None}}, "a.b", None),
            ([], "[0]", None),
            ([None], "[0]", None),
        ],
    )
    def test_none_handling(self, data, path, expected):
        """Test handling of None values."""
        assert get(data, path) == expected

    def test_nested_arrays(self, deep_nested_list: list[Any]):
        """Test deeply nested array access."""
        result = get(deep_nested_list, "[0].patient.list_of_dicts[*].num")
        expected = [
            item["num"] for item in deep_nested_list[0]["patient"]["list_of_dicts"]
        ]
        assert result == expected

    def test_type_mismatches(self):
        """Test behavior when accessing wrong types."""
        data = {"list": [1, 2, 3], "dict": {"key": "value"}}

        # Trying to index a dict - should return None
        result = get(data, "dict[0]")
        assert result is None

        # Trying to access property on list - returns list of None
        result = get(data, "list.property")
        assert result == [None, None, None]  # One None for each item in list
