"""Tests for the grab function."""

from typing import Any

import pytest

from chidian import grab


class TestGrabBasic:
    """Test basic grab operations."""

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
        result = grab(simple_data, path)

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
        assert grab(simple_data, "missing") is None
        assert grab(simple_data, "data.missing") is None
        assert grab(simple_data, "missing", default="DEFAULT") == "DEFAULT"

    def test_apply_function(self, simple_data: dict[str, Any]):
        """Test applying transformation functions."""
        result = grab(simple_data, "data.patient.id", apply=lambda x: x + "_modified")
        assert result == simple_data["data"]["patient"]["id"] + "_modified"


class TestGrabArrays:
    """Test grab operations on arrays."""

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
        result = grab(simple_data, path)
        expected = simple_data["list_data"][indices[0]]["patient"]
        assert result == expected

    def test_out_of_bounds_index(self, simple_data: dict[str, Any]):
        """Test behavior with out of bounds indices."""
        assert grab(simple_data, "list_data[5000].patient") is None

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
        result = grab(simple_data, path)
        start, stop = slice_params
        expected = simple_data["list_data"][start:stop]
        assert result == expected

    def test_slice_then_access(self, simple_data: dict[str, Any]):
        """Test slicing followed by property access."""
        result = grab(simple_data, "list_data[1:3].patient")
        expected = [item["patient"] for item in simple_data["list_data"][1:3]]
        assert result == expected

    def test_wildcard_on_list(self, list_data: list[Any]):
        """Test wildcard operations on lists."""
        assert grab(list_data, "[*].patient") == [p["patient"] for p in list_data]
        assert grab(list_data, "[:].patient.id") == [
            p["patient"]["id"] for p in list_data
        ]


class TestGrabEdgeCases:
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
        assert grab(data, path) == expected

    def test_nested_arrays(self, deep_nested_list: list[Any]):
        """Test deeply nested array access."""
        result = grab(deep_nested_list, "[0].patient.list_of_dicts[*].num")
        expected = [
            item["num"] for item in deep_nested_list[0]["patient"]["list_of_dicts"]
        ]
        assert result == expected

    def test_type_mismatches(self):
        """Test behavior when accessing wrong types."""
        data = {"list": [1, 2, 3], "dict": {"key": "value"}}

        # Trying to index a dict - should return None
        result = grab(data, "dict[0]")
        assert result is None

        # Trying to access property on list - returns list of None
        result = grab(data, "list.property")
        assert result == [None, None, None]


class TestGrabIntegration:
    """Integration tests for grab function."""

    def test_fhir_data(self, fhir_bundle: dict[str, Any]):
        """Test with FHIR-like data structures."""
        # Get all observation IDs
        ids = grab(fhir_bundle, "entry[*].resource.id")
        assert ids == ["bp-1", "bp-2"]

        # Get first observation's systolic value
        systolic = grab(
            fhir_bundle, "entry[0].resource.component[0].valueQuantity.value"
        )
        assert systolic == 120


class TestGrabShape:
    """Fan-out paths always return lists, regardless of list length."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            ({"u": [{"n": "a"}]}, ["a"]),
            ({"u": [{"n": "a"}, {"n": "b"}]}, ["a", "b"]),
            ({"u": []}, []),
            ({"u": [{"x": 1}]}, [None]),
        ],
    )
    def test_wildcard_returns_list(self, data, expected):
        assert grab(data, "u[*].n") == expected

    def test_key_over_single_item_list_returns_list(self):
        assert grab({"u": [{"n": "a"}]}, "u.n") == ["a"]

    def test_wildcard_on_single_item_list(self):
        assert grab({"u": [5]}, "u[*]") == [5]

    def test_non_fanout_paths_return_scalars(self):
        data = {"u": [{"n": "a"}]}
        assert grab(data, "u[0].n") == "a"
        assert grab(data, "u[0:1]") == [{"n": "a"}]

    def test_wildcard_on_non_list(self):
        assert grab({"u": 5}, "u[*]") is None


class TestGrabQuotedKeys:
    """Quoted bracket keys reach keys that aren't valid bare names."""

    @pytest.mark.parametrize(
        "data,path,expected",
        [
            ({"@id": 1}, '["@id"]', 1),
            ({"x": {"@id": 1}}, 'x["@id"]', 1),
            ({"x": {"a.b": 1}}, "x['a.b']", 1),
            ({"x": {"a b": 1}}, 'x["a b"]', 1),
            ({"0": {"y": 1}}, '["0"].y', 1),
            ({"x": {"@type": [{"v": 1}]}}, 'x["@type"][0].v', 1),
            ({"x": [{"@id": 1}, {"@id": 2}]}, 'x[*]["@id"]', [1, 2]),
            ({"a": 1, "@b": 2}, '(a, ["@b"])', (1, 2)),
        ],
    )
    def test_quoted_keys(self, data, path, expected):
        assert grab(data, path) == expected

    def test_whitespace_outside_quotes_ignored(self):
        assert grab({"x": [{"y": 1}]}, "x [ 0 ] . y") == 1


class TestGrabDefault:
    """default applies only when the path doesn't exist."""

    def test_default_not_used_for_explicit_none(self):
        assert grab({"x": None}, "x", default=9) is None

    def test_default_used_for_missing(self):
        assert grab({}, "x", default=9) == 9
        assert grab({"x": None}, "x.y", default=9) == 9
        assert grab({"x": []}, "x[0]", default=9) == 9

    def test_default_keeps_falsy_values(self):
        assert grab({"x": 0}, "x", default=9) == 0
        assert grab({"x": ""}, "x", default=9) == ""


class TestGrabApply:
    """apply errors are lenient by default and raise in strict mode."""

    def test_apply_error_returns_none(self):
        assert grab({"x": "z"}, "x", apply=int) is None

    def test_apply_error_raises_in_strict_mode(self):
        from chidian import mapping_context

        with mapping_context(strict=True):
            with pytest.raises(ValueError):
                grab({"x": "z"}, "x", apply=int)

    def test_apply_chain(self):
        assert grab({"x": "5"}, "x", apply=[int, lambda v: v * 2]) == 10
