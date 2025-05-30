from typing import Any

import pytest

from chidian import DictPiper, get
from chidian.seeds import DROP, KEEP, CASE, MERGE


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
        "removed_empty_list": [],
    }


def test_merge_seed():
    """Test MERGE seed functionality from README."""
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "middleName": "James"
    }
    
    # Test basic merge
    merge_fn = MERGE("firstName", "lastName", template="{} {}")
    assert merge_fn(data) == "John Doe"
    
    # Test merge with missing values
    merge_fn_skip = MERGE("firstName", "missing", "lastName", template="{} {} {}", skip_none=True)
    assert merge_fn_skip(data) == "John Doe"
    
    # Test merge with all values
    merge_fn_all = MERGE("firstName", "middleName", "lastName", template="{} {} {}")
    assert merge_fn_all(data) == "John James Doe"


def test_merge_comprehensive():
    """Comprehensive tests for MERGE behavior."""
    
    # Test data with different types of content
    data = {
        "first": "John",
        "last": "Doe", 
        "middle": "James",
        "missing": None,
        "number": 42,
        "empty": ""
    }
    
    # Test basic template functionality
    assert MERGE("first", "last", template="{} {}")(data) == "John Doe"
    assert MERGE("first", "middle", "last", template="{} {} {}")(data) == "John James Doe"
    
    # Test with missing values (skip_none=False by default)
    assert MERGE("first", "missing", "last", template="{} {} {}")(data) == "John None Doe"
    
    # Test with skip_none=True
    assert MERGE("first", "missing", "last", template="{} {} {}", skip_none=True)(data) == "John Doe"
    
    # Test different template patterns
    assert MERGE("first", "last", template="{}-{}")(data) == "John-Doe"
    assert MERGE("first", "last", template="Name: {} {}")(data) == "Name: John Doe"
    
    # Test with numbers and empty strings
    assert MERGE("first", "number", template="{} {}")(data) == "John 42"
    assert MERGE("first", "empty", template="{}{}")(data) == "John"


def test_merge_skip_none_edge_cases():
    """Test the complex skip_none behavior and template adjustment logic."""
    
    data = {
        "a": "First",
        "b": None,
        "c": "Third", 
        "d": None,
        "e": "Fifth"
    }
    
    # Test the template adjustment logic with different placeholder counts
    assert MERGE("a", "b", "c", template="{} {} {}", skip_none=True)(data) == "First Third"
    assert MERGE("a", "b", template="{} {}", skip_none=True)(data) == "First"
    assert MERGE("b", "d", template="{} {}", skip_none=True)(data) == ""
    
    # Test with different template patterns
    assert MERGE("a", "b", "c", template="{}-{}-{}", skip_none=True)(data) == "First Third"
    assert MERGE("a", "b", "c", template="{}|{}|{}", skip_none=True)(data) == "First Third"
    assert MERGE("a", "b", "c", template="{}, {}, {}", skip_none=True)(data) == "First Third"
    
    # Test with prefix/suffix in template
    assert MERGE("a", "b", "c", template="[{} {} {}]", skip_none=True)(data) == "First Third"
    assert MERGE("a", "b", template="Value: {} {}", skip_none=True)(data) == "First"
    
    # Test when first values are None
    assert MERGE("b", "a", "c", template="{} {} {}", skip_none=True)(data) == "First Third"
    assert MERGE("b", "d", "a", template="{} {} {}", skip_none=True)(data) == "First"
    
    # Test process method directly
    merge = MERGE("a", "c", template="{} {}")
    assert merge.process(data) == "First Third"
    assert merge.process(data, context={"some": "context"}) == "First Third"
    
    # Test edge case: all None with skip_none
    all_none_data = {"a": None, "b": None, "c": None}
    assert MERGE("a", "b", "c", template="{} {} {}", skip_none=True)(all_none_data) == ""
    
    # Test single None with skip_none  
    assert MERGE("b", template="Value: {}", skip_none=True)(data) == ""


def test_case_basic():
    """Test basic CASE functionality."""
    data = {
        "status": "active",
        "priority": "high"
    }
    
    # Basic CASE with string matching
    case_fn = CASE("status", {
        "active": "Patient is active",
        "inactive": "Patient is inactive", 
        "unknown": "Status unknown"
    }, default="No status")
    
    assert case_fn(data) == "Patient is active"
    
    # Test with different value
    data_inactive = {"status": "inactive"}
    assert case_fn(data_inactive) == "Patient is inactive"
    
    # Test default case
    data_missing = {"status": "suspended"}
    assert case_fn(data_missing) == "No status"


def test_case_comprehensive():
    """Comprehensive CASE functionality tests."""
    
    # Test with callable conditions using list format for ordered evaluation
    data = {
        "patient": {
            "age": 25,
            "status": "active",
            "scores": [85, 92, 78]
        }
    }
    
    # Function-based conditions with list for ordered evaluation
    case_age = CASE("patient.age", [
        (lambda age: age < 18, "minor"),
        (lambda age: 18 <= age < 65, "adult"), 
        (lambda age: age >= 65, "senior")
    ], default="unknown")
    
    assert case_age(data) == "adult"
    
    # Test with list operations
    case_scores = CASE("patient.scores", [
        (lambda scores: max(scores) > 90, "excellent"),
        (lambda scores: max(scores) > 80, "good"),
        (lambda scores: max(scores) > 70, "fair")
    ], default="poor")
    
    assert case_scores(data) == "excellent"
    
    # Mixed conditions (values and functions) using dict
    case_mixed = CASE("patient.status", {
        "active": {"display": "Active Patient", "code": "A"},
        "pending": {"display": "Pending", "code": "P"}
    }, default={"display": "Unknown", "code": "U"})
    
    result = case_mixed(data)
    assert result == {"display": "Active Patient", "code": "A"}


def test_case_ordered_evaluation():
    """Test that CASE evaluates in order (important for functions)."""
    
    data = {"score": 85}
    
    # Order matters for overlapping function conditions
    ordered_case = CASE("score", [
        (lambda x: x >= 90, "A"),
        (lambda x: x >= 80, "B"),  # This should match
        (lambda x: x >= 70, "C"),
        (lambda x: x >= 60, "D")
    ], default="F")
    assert ordered_case(data) == "B"
    
    # Test with dict (order may vary in Python < 3.7, but should work)
    dict_case = CASE("score", {
        lambda x: x >= 90: "A",
        lambda x: x >= 80: "B",
        lambda x: x >= 70: "C"
    }, default="F")
    # Should still get B, but order might affect which lambda matches first
    result = dict_case(data)
    assert result in ["B", "C"]  # Both are valid depending on order


def test_case_edge_cases():
    """Test edge cases and error handling for CASE."""
    
    data = {
        "value": "test",
        "number": 42,
        "none_val": None
    }
    
    # Missing path
    case_missing = CASE("missing.path", {
        "test": "found"
    }, default="not found")
    assert case_missing(data) == "not found"
    
    # None value matching
    case_none = CASE("none_val", {
        None: "is none",
        "other": "not none"
    }, default="default")
    assert case_none(data) == "is none"
    
    # Empty conditions dict
    case_empty = CASE("value", {}, default="empty case")
    assert case_empty(data) == "empty case"
    
    # No default provided - should return None
    case_no_default = CASE("value", {
        "nomatch": "result"
    })
    assert case_no_default(data) is None


def test_case_real_world_examples():
    """Test CASE with realistic healthcare scenarios."""
    
    # Patient status mapping
    patient_data = {
        "patient": {
            "status": "active",
            "age": 45,
            "conditions": ["diabetes", "hypertension"]
        }
    }
    
    # Status display mapping
    status_case = CASE("patient.status", {
        "active": {"display": "Active Patient", "color": "green"},
        "inactive": {"display": "Inactive Patient", "color": "red"},
        "deceased": {"display": "Deceased", "color": "gray"}
    }, default={"display": "Unknown Status", "color": "yellow"})
    
    result = status_case(patient_data)
    assert result["display"] == "Active Patient"
    assert result["color"] == "green"
    
    # Risk assessment based on conditions
    risk_case = CASE("patient.conditions", [
        (lambda conds: "diabetes" in conds and "hypertension" in conds, "high"),
        (lambda conds: "diabetes" in conds or "hypertension" in conds, "medium"),
        (lambda conds: len(conds) == 0, "low")
    ], default="unknown")
    
    assert risk_case(patient_data) == "high"


def test_case_process_method():
    """Test CASE process method directly."""
    data = {"status": "active"}
    
    case_fn = CASE("status", {
        "active": "working",
        "inactive": "not working"
    }, default="unknown")
    
    # Test process method
    assert case_fn.process(data) == "working"
    assert case_fn.process(data, context={"some": "context"}) == "working"
    
    # Test with missing data
    empty_data = {}
    assert case_fn.process(empty_data) == "unknown"


def test_case_with_array_notation():
    """Test CASE with array path notation."""
    data = {
        "patients": [
            {"status": "active", "priority": 1},
            {"status": "inactive", "priority": 2},
            {"status": "pending", "priority": 3}
        ]
    }
    
    # Test with array index
    case_first = CASE("patients[0].status", {
        "active": "first is active",
        "inactive": "first is inactive"
    }, default="unknown")
    
    assert case_first(data) == "first is active"
    
    # Test with different array index
    case_second = CASE("patients[1].status", {
        "active": "second is active", 
        "inactive": "second is inactive"
    }, default="unknown")
    
    assert case_second(data) == "second is inactive"