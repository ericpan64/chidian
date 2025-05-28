from typing import Any

import pytest

from chidian import DictPiper, get
from chidian.seeds import DROP, KEEP


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
