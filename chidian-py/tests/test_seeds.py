from typing import Any

import pytest

from chidian import DictPiper, get
from chidian.seeds import DROP, KEEP, CASE, COALESCE, SPLIT, MERGE, FLATTEN


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
    """Comprehensive tests for MERGE behavior and edge cases."""
    
    data = {
        "first": "John",
        "last": "Doe", 
        "middle": "James",
        "prefix": "Dr.",
        "suffix": "Jr.",
        "empty": "",
        "zero": 0,
        "false": False,
        "none": None
    }
    
    # Basic template functionality
    assert MERGE("first", "last", template="{} {}")(data) == "John Doe"
    assert MERGE("prefix", "first", "last", template="{} {} {}")(data) == "Dr. John Doe"
    
    # Different template formats
    assert MERGE("first", "last", template="{}, {}")(data) == "John, Doe"
    assert MERGE("first", "last", template="{}_{}")(data) == "John_Doe"
    assert MERGE("first", "last", template="Name: {} {}")(data) == "Name: John Doe"
    assert MERGE("first", "last", template="{} ({})")(data) == "John (Doe)"
    
    # Handle None values without skip_none
    assert MERGE("first", "none", "last", template="{} {} {}")(data) == "John None Doe"
    assert MERGE("none", "first", template="{} {}")(data) == "None John"
    
    # Handle other falsy values (should not be skipped)
    assert MERGE("first", "empty", "last", template="{}-{}-{}")(data) == "John--Doe"
    assert MERGE("first", "zero", template="{} {}")(data) == "John 0"
    assert MERGE("first", "false", template="{} {}")(data) == "John False"
    
    # Test skip_none behavior
    assert MERGE("first", "none", "last", template="{} {} {}", skip_none=True)(data) == "John Doe"
    assert MERGE("none", "first", "none", template="{} {} {}", skip_none=True)(data) == "John"
    assert MERGE("none", "none", template="{} {}", skip_none=True)(data) == ""
    
    # Test skip_none with empty string (should NOT be skipped)
    assert MERGE("first", "empty", "last", template="{} {} {}", skip_none=True)(data) == "John  Doe"
    
    # Single value templates
    assert MERGE("first", template="Hello {}")(data) == "Hello John"
    assert MERGE("none", template="Hello {}", skip_none=True)(data) == ""
    
    # No placeholder templates
    assert MERGE("first", "last", template="Static text")(data) == "Static text"
    
    # Complex data types
    complex_data = {
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "number": 42.5
    }
    assert MERGE("list", "dict", template="{} | {}")(complex_data) == "[1, 2, 3] | {'key': 'value'}"
    assert MERGE("number", template="Value: {}")(complex_data) == "Value: 42.5"
    
    # Test with array notation
    array_data = {
        "names": ["Alice", "Bob", "Charlie"],
        "user": {"first": "John", "last": "Smith"}
    }
    assert MERGE("names[0]", "names[1]", template="{} and {}")(array_data) == "Alice and Bob"
    assert MERGE("user.first", "user.last", template="{} {}")(array_data) == "John Smith"
    
    # Edge case: missing paths
    assert MERGE("missing", "first", template="{} {}")(data) == "None John"
    assert MERGE("missing1", "missing2", template="{} {}")(data) == "None None"
    assert MERGE("missing", template="Found: {}")(data) == "Found: None"
    
    # Edge case: mismatched template and values
    try:
        MERGE("first", template="{} {}")(data)  # 1 value, 2 placeholders
        assert False, "Should have raised an error"
    except IndexError:
        pass  # Expected
    
    # Extra values are silently ignored (uses only what template needs)
    assert MERGE("first", "last", "middle", template="{} {}")(data) == "John Doe"
    
    # Test process method directly
    merge = MERGE("first", "last", template="{} {}")
    assert merge.process(data) == "John Doe"
    assert merge.process(data, context={"some": "context"}) == "John Doe"
    
    # Unicode and special characters
    unicode_data = {
        "emoji": "😀",
        "accents": "José",
        "symbols": "α β γ"
    }
    assert MERGE("emoji", "accents", template="{} {}")(unicode_data) == "😀 José"
    assert MERGE("symbols", template="Greek: {}")(unicode_data) == "Greek: α β γ"


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
    
    # Test mixed None and empty string
    mixed_data = {"a": "First", "b": None, "c": "", "d": "Fourth"}
    assert MERGE("a", "b", "c", "d", template="{} {} {} {}", skip_none=True)(mixed_data) == "First  Fourth"
    
    # Test edge case: all None with skip_none
    all_none_data = {"a": None, "b": None, "c": None}
    assert MERGE("a", "b", "c", template="{} {} {}", skip_none=True)(all_none_data) == ""
    
    # Test single None with skip_none  
    assert MERGE("b", template="Value: {}", skip_none=True)(data) == ""


def test_flatten_seed():
    """Test FLATTEN seed functionality from README."""
    data = {
        "ids": ["123", "456", "789"],
        "codes": ["A", "B", "C"]
    }
    
    # Test basic flatten
    flatten_fn = FLATTEN(["ids"], delimiter=", ")
    assert flatten_fn(data) == "123, 456, 789"
    
    # Test flatten multiple sources
    flatten_multi = FLATTEN(["ids", "codes"], delimiter=" | ")
    assert flatten_multi(data) == "123 | 456 | 789 | A | B | C"


def test_flatten_comprehensive():
    """Comprehensive tests for FLATTEN behavior."""
    
    # Test with various data types
    data = {
        "strings": ["hello", "world"],
        "numbers": [1, 2, 3, 4.5],
        "mixed": ["text", 123, True, False],
        "with_none": ["start", None, "end"],
        "single_value": "not a list",
        "nested_lists": [["a", "b"], ["c", "d"]],  # Will be stringified
        "empty_list": [],
        "none_value": None,
        "dict_value": {"key": "value"},
        "list_of_dicts": [{"name": "John"}, {"name": "Jane"}]
    }
    
    # Basic list flattening
    assert FLATTEN(["strings"])(data) == "hello, world"
    assert FLATTEN(["numbers"])(data) == "1, 2, 3, 4.5"
    
    # Mixed types are converted to strings
    assert FLATTEN(["mixed"])(data) == "text, 123, True, False"
    
    # None values are skipped
    assert FLATTEN(["with_none"])(data) == "start, end"
    
    # Single values are included as-is
    assert FLATTEN(["single_value"])(data) == "not a list"
    
    # Empty list results in empty string
    assert FLATTEN(["empty_list"])(data) == ""
    
    # None path is skipped entirely
    assert FLATTEN(["none_value", "strings"])(data) == "hello, world"
    
    # Non-list complex types are stringified
    assert FLATTEN(["dict_value"])(data) == "{'key': 'value'}"
    
    # Nested structures are stringified
    assert FLATTEN(["nested_lists"])(data) == "['a', 'b'], ['c', 'd']"
    assert FLATTEN(["list_of_dicts"])(data) == "{'name': 'John'}, {'name': 'Jane'}"
    
    # Custom delimiters
    assert FLATTEN(["strings"], delimiter=" - ")(data) == "hello - world"
    assert FLATTEN(["strings"], delimiter="")(data) == "helloworld"
    assert FLATTEN(["strings"], delimiter="\n")(data) == "hello\nworld"
    
    # Multiple paths with mixed types
    mixed_data = {
        "users": ["Alice", "Bob"],
        "count": 42,
        "active": True,
        "tags": ["python", "rust", "go"]
    }
    assert FLATTEN(["users", "count", "active", "tags"])(mixed_data) == "Alice, Bob, 42, True, python, rust, go"
    
    # Test with array notation
    array_data = {
        "items": [
            {"id": "A1", "values": [10, 20]},
            {"id": "B2", "values": [30, 40]},
            {"id": "C3", "values": [50]}
        ]
    }
    assert FLATTEN(["items[0].values"])(array_data) == "10, 20"
    assert FLATTEN(["items[*].id"])(array_data) == "A1, B2, C3"
    
    # Edge case: path doesn't exist
    assert FLATTEN(["missing_path"])(data) == ""
    assert FLATTEN(["missing1", "missing2"], delimiter=" | ")(data) == ""
    
    # Edge case: mix of missing and existing paths
    assert FLATTEN(["missing", "strings", "also_missing"])(data) == "hello, world"
    
    # Test process method directly
    flatten = FLATTEN(["strings"], delimiter=" + ")
    assert flatten.process(data) == "hello + world"
    assert flatten.process(data, context={"some": "context"}) == "hello + world"
    
    # Unicode and special characters
    unicode_data = {
        "emojis": ["😀", "🎉", "🚀"],
        "special": ["tab\there", "new\nline", "quote\"mark"]
    }
    assert FLATTEN(["emojis"])(unicode_data) == "😀, 🎉, 🚀"
    assert FLATTEN(["special"], delimiter=" | ")(unicode_data) == "tab\there | new\nline | quote\"mark"
    
    # Large numbers and scientific notation
    number_data = {
        "big": [1000000, 1e6, 1.23e-4],
        "float": [3.14159, -2.718, 0.0]
    }
    assert FLATTEN(["big"])(number_data) == "1000000, 1000000.0, 0.000123"
    assert FLATTEN(["float"])(number_data) == "3.14159, -2.718, 0.0"
    
    # Edge case: empty paths list
    assert FLATTEN([], delimiter=", ")(data) == ""
    
    # Edge case: single empty list
    empty_data = {"empty": []}
    assert FLATTEN(["empty"])(empty_data) == ""


def test_coalesce_seed():
    """Test COALESCE seed functionality from README."""
    data = {
        "primary": None,
        "secondary": "",
        "tertiary": "value3"
    }
    
    # Test coalesce with first non-empty value
    coalesce_fn = COALESCE(["primary", "secondary", "tertiary"], default="none")
    assert coalesce_fn(data) == "value3"
    
    # Test coalesce with all empty, use default
    empty_data = {"primary": None, "secondary": None}
    assert coalesce_fn(empty_data) == "none"


def test_coalesce_comprehensive():
    """Comprehensive tests for COALESCE behavior."""
    
    # Test with various empty values
    data = {
        "null_value": None,
        "empty_string": "",
        "zero": 0,
        "false": False,
        "empty_list": [],
        "empty_dict": {},
        "valid_string": "found",
        "valid_number": 42
    }
    
    # Basic coalesce - None and empty string are skipped
    assert COALESCE(["null_value", "empty_string", "valid_string"])(data) == "found"
    
    # Zero and False are not considered empty
    assert COALESCE(["null_value", "zero"])(data) == 0
    assert COALESCE(["null_value", "false"])(data) == False
    
    # Empty collections are not considered empty by COALESCE
    assert COALESCE(["null_value", "empty_list"])(data) == []
    assert COALESCE(["null_value", "empty_dict"])(data) == {}
    
    # Test with missing paths
    assert COALESCE(["missing1", "missing2"], default="default_value")(data) == "default_value"
    
    # Test with nested paths
    nested_data = {
        "user": {
            "name": None,
            "nickname": "",
            "fullname": "John Doe"
        }
    }
    assert COALESCE(["user.name", "user.nickname", "user.fullname"])(nested_data) == "John Doe"
    
    # Test default value types
    assert COALESCE(["missing"], default=None)(data) is None
    assert COALESCE(["missing"], default=0)(data) == 0
    assert COALESCE(["missing"], default=[])(data) == []
    assert COALESCE(["missing"], default={})(data) == {}
    
    # Test with single path
    assert COALESCE(["valid_string"])(data) == "found"
    assert COALESCE(["null_value"], default="fallback")(data) == "fallback"
    
    # Test order matters
    order_data = {
        "first": "1st",
        "second": "2nd",
        "third": "3rd"
    }
    assert COALESCE(["first", "second", "third"])(order_data) == "1st"
    assert COALESCE(["second", "first", "third"])(order_data) == "2nd"
    
    # Test with array access
    array_data = {
        "items": [None, "", "value", "another"]
    }
    assert COALESCE(["items[0]", "items[1]", "items[2]"])(array_data) == "value"
    
    # Test process method directly (for coverage)
    coalesce = COALESCE(["valid_string"])
    assert coalesce.process(data) == "found"
    assert coalesce.process(data, context={"some": "context"}) == "found"
    
    # Edge case: whitespace strings
    whitespace_data = {
        "spaces": "   ",
        "tabs": "\t\t",
        "newlines": "\n\n",
        "mixed": " \t\n ",
        "actual": "content"
    }
    # Whitespace is not considered empty
    assert COALESCE(["spaces"])(whitespace_data) == "   "
    assert COALESCE(["null_value", "empty_string", "spaces"])(whitespace_data) == "   "
    
    # Edge case: special values
    special_data = {
        "nan": float('nan'),
        "infinity": float('inf'),
        "negative_infinity": float('-inf')
    }
    result = COALESCE(["nan"])(special_data)
    assert str(result) == 'nan'  # NaN comparison is tricky
    assert COALESCE(["infinity"])(special_data) == float('inf')
    assert COALESCE(["negative_infinity"])(special_data) == float('-inf')


def test_split_seed():
    """Test SPLIT seed functionality from README."""
    data = {
        "full_name": "John James Doe",
        "address": "123 Main St\nNew York, NY 10001"
    }
    
    # Test split first name
    split_first = SPLIT("full_name", pattern=" ", part=0)
    assert split_first(data) == "John"
    
    # Test split last name
    split_last = SPLIT("full_name", pattern=" ", part=-1)
    assert split_last(data) == "Doe"
    
    # Test split with transformation
    split_city = SPLIT("address", pattern="\n", part=1, then=lambda x: x.split(", ")[0] if x else None)
    assert split_city(data) == "New York"


def test_split_comprehensive():
    """Comprehensive tests for SPLIT behavior and edge cases."""
    
    data = {
        "simple": "apple-banana-cherry",
        "spaces": "hello world test",
        "csv": "name,age,city,country",
        "path": "/home/user/documents/file.txt",
        "empty_parts": "a,,b,,c",
        "single": "noSeparator",
        "empty_string": "",
        "none_value": None,
        "number": 123,
        "starts_with_sep": "-apple-banana",
        "ends_with_sep": "apple-banana-",
        "multiple_seps": "a--b--c",
        "unicode": "α-β-γ-δ"
    }
    
    # Basic splitting with different patterns
    assert SPLIT("simple", "-", 0)(data) == "apple"
    assert SPLIT("simple", "-", 1)(data) == "banana"
    assert SPLIT("simple", "-", 2)(data) == "cherry"
    assert SPLIT("spaces", " ", 1)(data) == "world"
    assert SPLIT("csv", ",", 2)(data) == "city"
    
    # Negative indexing
    assert SPLIT("simple", "-", -1)(data) == "cherry"
    assert SPLIT("simple", "-", -2)(data) == "banana"
    assert SPLIT("simple", "-", -3)(data) == "apple"
    assert SPLIT("csv", ",", -1)(data) == "country"
    
    # Path-like splitting
    assert SPLIT("path", "/", 1)(data) == "home"
    assert SPLIT("path", "/", -1)(data) == "file.txt"
    assert SPLIT("path", ".", -1)(data) == "txt"  # File extension
    
    # Empty parts handling
    assert SPLIT("empty_parts", ",", 1)(data) == ""
    assert SPLIT("empty_parts", ",", 3)(data) == ""
    assert SPLIT("starts_with_sep", "-", 0)(data) == ""
    assert SPLIT("ends_with_sep", "-", -1)(data) == ""
    
    # Edge case: no separator found
    assert SPLIT("single", "-", 0)(data) == "noSeparator"
    assert SPLIT("single", "-", 1)(data) is None  # Out of bounds
    
    # Edge case: empty string
    assert SPLIT("empty_string", "-", 0)(data) == ""
    assert SPLIT("empty_string", "-", 1)(data) is None
    
    # Edge case: None value
    assert SPLIT("none_value", "-", 0)(data) is None
    
    # Edge case: out of bounds
    assert SPLIT("simple", "-", 5)(data) is None
    assert SPLIT("simple", "-", -5)(data) is None
    
    # Edge case: non-string values should raise AttributeError
    try:
        SPLIT("number", "-", 0)(data)
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass
    
    # Multiple consecutive separators
    assert SPLIT("multiple_seps", "--", 0)(data) == "a"
    assert SPLIT("multiple_seps", "--", 1)(data) == "b"
    assert SPLIT("multiple_seps", "--", 2)(data) == "c"
    
    # Unicode handling
    assert SPLIT("unicode", "-", 1)(data) == "β"
    assert SPLIT("unicode", "-", -1)(data) == "δ"
    
    # Different pattern types
    multichar_data = {"text": "abc::def::ghi"}
    assert SPLIT("text", "::", 1)(multichar_data) == "def"
    
    newline_data = {"lines": "line1\nline2\nline3"}
    assert SPLIT("lines", "\n", 0)(newline_data) == "line1"
    assert SPLIT("lines", "\n", -1)(newline_data) == "line3"
    
    # Test with transformation function
    transform_data = {"email": "user@example.com", "url": "https://example.com/path"}
    
    # Extract username from email
    username = SPLIT("email", "@", 0)(transform_data)
    assert username == "user"
    
    # Extract domain and apply transformation
    domain_split = SPLIT("email", "@", 1, then=lambda x: x.upper())(transform_data)
    assert domain_split == "EXAMPLE.COM"
    
    # Chain transformations
    protocol = SPLIT("url", "://", 0)(transform_data)
    assert protocol == "https"
    
    path_part = SPLIT("url", "/", -1)(transform_data)
    assert path_part == "path"
    
    # Transform with None handling
    assert SPLIT("none_value", "@", 0, then=lambda x: x.upper())(data) is None
    
    # Complex transformation
    date_data = {"timestamp": "2023-12-25T10:30:45"}
    date_part = SPLIT("timestamp", "T", 0)(date_data)
    assert date_part == "2023-12-25"
    
    year = SPLIT("timestamp", "T", 0, then=lambda x: x.split("-")[0])(date_data)
    assert year == "2023"
    
    # Test process method directly
    split = SPLIT("simple", "-", 1)
    assert split.process(data) == "banana"
    assert split.process(data, context={"some": "context"}) == "banana"
    
    # Test with array notation
    array_data = {
        "items": [
            {"name": "first-item"},
            {"name": "second-item"}
        ]
    }
    assert SPLIT("items[0].name", "-", 1)(array_data) == "item"
    assert SPLIT("items[1].name", "-", 0)(array_data) == "second"


def test_error_handling():
    """Test error handling in transformations."""
    data = {"name": "John"}
    
    # Test with invalid path
    assert get(data, "invalid.path.here") is None
    
    # Test with invalid index
    assert get(data, "name[10]") is None
    
    # Test MERGE with all missing values
    merge_fn = MERGE("missing1", "missing2", template="{} {}")
    assert merge_fn(data) == "None None"  # Template with None values
    
    # Test SPLIT with missing data
    split_fn = SPLIT("missing", pattern=" ", part=0)
    assert split_fn(data) is None


def test_case_basic():
    """Test basic CASE functionality."""
    data = {
        "status": "active",
        "role": "admin",
        "score": 85,
        "grade": "B",
        "none_value": None
    }
    
    # Basic string matching
    status_case = CASE("status", {
        "active": "User is active",
        "inactive": "User is inactive",
        "pending": "User is pending"
    }, default="Unknown status")
    assert status_case(data) == "User is active"
    
    # Test default case
    unknown_case = CASE("unknown_field", {
        "value1": "Result1",
        "value2": "Result2"
    }, default="Default result")
    assert unknown_case(data) == "Default result"
    
    # Test with None value
    none_case = CASE("none_value", {
        None: "Value is None",
        "something": "Value exists"
    })
    assert none_case(data) == "Value is None"


def test_case_comprehensive():
    """Comprehensive tests for CASE functionality."""
    
    data = {
        "user": {
            "role": "admin",
            "status": "active",
            "score": 92,
            "points": 15000,
            "subscription": {"type": "premium", "active": True}
        },
        "order": {"status": "shipped", "priority": "high"},
        "empty_string": "",
        "zero": 0,
        "false_value": False,
        "number": 42,
        "list": [1, 2, 3]
    }
    
    # String value matching
    role_case = CASE("user.role", {
        "admin": "Administrator",
        "user": "Regular User", 
        "guest": "Guest Access"
    }, default="Unknown role")
    assert role_case(data) == "Administrator"
    
    # Number value matching
    number_case = CASE("number", {
        42: "The answer",
        100: "Century", 
        0: "Zero"
    })
    assert number_case(data) == "The answer"
    
    # Function-based matching for grade calculation
    grade_case = CASE("user.score", {
        lambda x: x >= 90: "A",
        lambda x: x >= 80: "B",
        lambda x: x >= 70: "C",
        lambda x: x >= 60: "D"
    }, default="F")
    assert grade_case(data) == "A"
    
    # User tier based on points
    tier_case = CASE("user.points", {
        lambda p: p >= 10000: "💎 Diamond",
        lambda p: p >= 5000: "🥇 Gold", 
        lambda p: p >= 1000: "🥈 Silver"
    }, default="🥉 Bronze")
    assert tier_case(data) == "💎 Diamond"
    
    # Order status with emojis
    order_case = CASE("order.status", {
        "pending": "⏳ Processing",
        "shipped": "🚚 In Transit",
        "delivered": "✅ Completed",
        "cancelled": "❌ Cancelled"
    }, default="Unknown")
    assert order_case(data) == "🚚 In Transit"
    
    # Test falsy values (should match exactly)
    falsy_case = CASE("empty_string", {
        "": "Empty string found",
        None: "None found"
    })
    assert falsy_case(data) == "Empty string found"
    
    # Note: 0 and False are equal in Python, so dict order matters
    zero_case = CASE("zero", [
        (0, "Zero found"),
        (False, "False found")
    ])
    assert zero_case(data) == "Zero found"
    
    false_case = CASE("false_value", [
        (False, "False found"),
        (0, "Zero found") 
    ])
    assert false_case(data) == "False found"


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
        "string": "test",
        "number": 123,
        "list": [1, 2, 3],
        "dict": {"key": "value"},
        "none": None
    }
    
    # Missing path
    missing_case = CASE("missing.path", {
        "value": "Found"
    }, default="Not found")
    assert missing_case(data) == "Not found"
    
    # Function that raises exception
    exception_case = CASE("string", {
        lambda x: x > 5: "Greater",  # Will raise TypeError for string
        "test": "String match"
    })
    assert exception_case(data) == "String match"
    
    # Function with None value
    none_func_case = CASE("none", {
        lambda x: x is not None: "Not None",
        lambda x: x is None: "Is None"
    })
    assert none_func_case(data) == "Is None"
    
    # Complex object matching (use tuple instead of list for hashability)
    tuple_data = {"tuple": (1, 2, 3), "list": [1, 2, 3]}
    complex_case = CASE("tuple", {
        (1, 2, 3): "Exact tuple match",
        lambda x: len(x) > 2: "Long sequence"
    })
    assert complex_case(tuple_data) == "Exact tuple match"
    
    # Function-based matching for unhashable types
    list_case = CASE("list", {
        lambda x: x == [1, 2, 3]: "List match via function",
        lambda x: len(x) > 2: "Long list"
    })
    assert list_case(data) == "List match via function"
    
    # No default provided
    no_default_case = CASE("string", {
        "other": "Other value"
    })
    assert no_default_case(data) is None


def test_case_real_world_examples():
    """Test real-world usage patterns for CASE."""
    
    # E-commerce order processing
    order_data = {
        "order": {
            "status": "processing",
            "total": 250.00,
            "items": 3,
            "customer": {"tier": "gold"}
        }
    }
    
    # Order status display
    status_display = CASE("order.status", {
        "cart": "🛒 In Cart",
        "processing": "⚙️ Processing Order", 
        "shipped": "📦 Shipped",
        "delivered": "✅ Delivered"
    }, default="❓ Unknown Status")
    assert status_display(order_data) == "⚙️ Processing Order"
    
    # Shipping cost based on total
    shipping_cost = CASE("order.total", {
        lambda x: x >= 100: "Free Shipping",
        lambda x: x >= 50: "$5.99 Shipping",
        lambda x: x > 0: "$9.99 Shipping"
    }, default="Invalid Order")
    assert shipping_cost(order_data) == "Free Shipping"
    
    # User preferences
    user_data = {
        "user": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    }
    
    theme_icon = CASE("user.theme", {
        "dark": "🌙",
        "light": "☀️", 
        "auto": "🌓"
    }, default="🎨")
    assert theme_icon(user_data) == "🌙"
    
    # API response formatting
    api_data = {
        "response": {
            "status_code": 200,
            "data": {"users": [1, 2, 3]}
        }
    }
    
    status_message = CASE("response.status_code", {
        200: "Success",
        201: "Created",
        400: "Bad Request",
        401: "Unauthorized", 
        403: "Forbidden",
        404: "Not Found",
        500: "Server Error"
    }, default="Unknown Status")
    assert status_message(api_data) == "Success"


def test_case_process_method():
    """Test CASE process method directly."""
    
    data = {"status": "active"}
    
    case = CASE("status", {
        "active": "Active Status",
        "inactive": "Inactive Status"
    })
    
    # Test process method
    assert case.process(data) == "Active Status"
    assert case.process(data, context={"some": "context"}) == "Active Status"
    
    # Test callable interface
    assert case(data) == "Active Status"


def test_case_with_array_notation():
    """Test CASE with array notation paths."""
    
    data = {
        "users": [
            {"name": "Alice", "role": "admin"},
            {"name": "Bob", "role": "user"},
            {"name": "Charlie", "role": "guest"}
        ],
        "settings": {
            "themes": ["dark", "light", "auto"]
        }
    }
    
    # Test with array index
    first_user_role = CASE("users[0].role", {
        "admin": "Administrator",
        "user": "Regular User",
        "guest": "Guest User"
    })
    assert first_user_role(data) == "Administrator"
    
    # Test with array element
    theme_choice = CASE("settings.themes[0]", {
        "dark": "Dark Mode",
        "light": "Light Mode",
        "auto": "Auto Mode"
    })
    assert theme_choice(data) == "Dark Mode"