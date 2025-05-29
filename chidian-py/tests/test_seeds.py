from typing import Any

import pytest

from chidian import DictPiper, get
from chidian.seeds import DROP, KEEP, COALESCE, SPLIT, MERGE, FLATTEN


def test_drop(simple_data: dict[str, Any]) -> None:
    source = simple_data

    def mapping(d: dict[str, Any]) -> dict[str, Any]:
        return {
            "CASE_parent_keep": {
                "CASE_curr_drop": {
                    "a": DROP.THIS_OBJECT,
                    "b": "someValue",
                },
                "CASE_curr_keep": {"id": get(d, "data.patient.id")},
            },
            "CASE_list": [DROP.THIS_OBJECT],
            "CASE_list_of_objects": [
                {"a": DROP.PARENT, "b": "someValue"},
                {"a": "someValue", "b": "someValue"},
            ],
        }

    piper = DictPiper(mapping, remove_empty=True)
    res = piper(source)
    assert res == {"CASE_parent_keep": {"CASE_curr_keep": {"id": get(source, "data.patient.id")}}}


def test_drop_out_of_bounds() -> None:
    source: dict[str, Any] = {}

    def mapping(_: dict[str, Any]) -> dict[str, Any]:
        return {"parent": {"CASE_no_grandparent": DROP.GREATGRANDPARENT}}

    piper = DictPiper(mapping)
    with pytest.raises(RuntimeError):
        _ = piper(source)


def test_drop_exact_level() -> None:
    source: dict[str, Any] = {}

    def mapping(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "parent": {"CASE_has_parent_object": DROP.PARENT},
            "other_data": 123,
        }

    piper = DictPiper(mapping)
    res = piper(source)
    assert res == {}


def test_drop_repeat() -> None:
    source: dict[str, Any] = {}

    def mapping(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "dropped_direct": [DROP.THIS_OBJECT, DROP.THIS_OBJECT],
            "also_dropped": [{"parent_key": DROP.PARENT}, DROP.THIS_OBJECT],
            "partially_dropped": [
                "first_kept",
                {"second_dropped": DROP.THIS_OBJECT},
                "third_kept",
                {"fourth_dropped": DROP.THIS_OBJECT},
            ],
        }

    piper = DictPiper(mapping)
    res = piper(source)
    assert res == {"partially_dropped": ["first_kept", "third_kept"]}


def test_keep() -> None:
    source: dict[str, Any] = {}

    def mapping(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "empty_vals": [KEEP({}), KEEP([]), KEEP(""), KEEP(None)],
            "nested_vals": {
                "dict": KEEP({}),
                "list": KEEP([]),
                "str": KEEP(""),
                "none": KEEP(None),
                "other_static_val": KEEP("Abc"),  # Expect this to de-serialize
            },
            "static_val": "Def",
            "empty_list": KEEP([]),
            "removed_empty_list": [],
        }

    piper = DictPiper(mapping)
    res = piper(source)
    assert KEEP({}).value == dict()
    assert KEEP([]).value == list()
    assert KEEP("").value == ""
    assert KEEP(None).value == None
    assert res == {
        "empty_vals": [{}, [], "", None],
        "nested_vals": {"dict": {}, "list": [], "str": "", "none": None, "other_static_val": "Abc"},
        "static_val": "Def",
        "empty_list": [],
    }


def test_merge_seed():
    """Test MERGE seed functionality from README."""
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "middleName": "James"
    }
    
    # Test basic merge
    merge_fn = MERGE(get, "firstName", "lastName", template="{} {}")
    assert merge_fn(data) == "John Doe"
    
    # Test merge with missing values
    merge_fn_skip = MERGE(get, "firstName", "missing", "lastName", template="{} {} {}", skip_none=True)
    assert merge_fn_skip(data) == "John Doe"
    
    # Test merge with all values
    merge_fn_all = MERGE(get, "firstName", "middleName", "lastName", template="{} {} {}")
    assert merge_fn_all(data) == "John James Doe"


def test_flatten_seed():
    """Test FLATTEN seed functionality from README."""
    data = {
        "ids": ["123", "456", "789"],
        "codes": ["A", "B", "C"]
    }
    
    # Test basic flatten
    flatten_fn = FLATTEN(get, ["ids"], delimiter=", ")
    assert flatten_fn(data) == "123, 456, 789"
    
    # Test flatten multiple sources
    flatten_multi = FLATTEN(get, ["ids", "codes"], delimiter=" | ")
    assert flatten_multi(data) == "123 | 456 | 789 | A | B | C"


def test_coalesce_seed():
    """Test COALESCE seed functionality from README."""
    data = {
        "primary": None,
        "secondary": "",
        "tertiary": "value3"
    }
    
    # Test coalesce with first non-empty value
    coalesce_fn = COALESCE(get, ["primary", "secondary", "tertiary"], default="none")
    assert coalesce_fn(data) == "value3"
    
    # Test coalesce with all empty, use default
    empty_data = {"primary": None, "secondary": None}
    assert coalesce_fn(empty_data) == "none"


def test_split_seed():
    """Test SPLIT seed functionality from README."""
    data = {
        "full_name": "John James Doe",
        "address": "123 Main St\nNew York, NY 10001"
    }
    
    # Test split first name
    split_first = SPLIT(get, "full_name", pattern=" ", part=0)
    assert split_first(data) == "John"
    
    # Test split last name
    split_last = SPLIT(get, "full_name", pattern=" ", part=-1)
    assert split_last(data) == "Doe"
    
    # Test split with transformation
    split_city = SPLIT(get, "address", pattern="\n", part=1, then=lambda x: x.split(", ")[0] if x else None)
    assert split_city(data) == "New York"


def test_error_handling():
    """Test error handling in transformations."""
    data = {"name": "John"}
    
    # Test with invalid path
    assert get(data, "invalid.path.here") is None
    
    # Test with invalid index
    assert get(data, "name[10]") is None
    
    # Test MERGE with all missing values
    merge_fn = MERGE(get, "missing1", "missing2", template="{} {}")
    assert merge_fn(data) == "None None"  # Template with None values
    
    # Test SPLIT with missing data
    split_fn = SPLIT(get, "missing", pattern=" ", part=0)
    assert split_fn(data) is None