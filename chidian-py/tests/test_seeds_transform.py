from typing import Any

import pytest

from chidian import DictPiper
from chidian.seeds import COALESCE, SPLIT, FLATTEN


def test_flatten_seed():
    """Test FLATTEN seed functionality from README."""
    data = {
        "names": ["Alice", "Bob", "Charlie"],
        "codes": ["A1", "B2", "C3"]
    }
    
    # Test basic flattening
    flatten_fn = FLATTEN(["names", "codes"])
    assert flatten_fn(data) == "Alice, Bob, Charlie, A1, B2, C3"
    
    # Test with custom delimiter
    flatten_custom = FLATTEN(["names"], delimiter=" | ")
    assert flatten_custom(data) == "Alice | Bob | Charlie"


def test_flatten_comprehensive():
    """Comprehensive tests for FLATTEN behavior."""
    
    # Complex nested data
    data = {
        "strings": ["hello", "world"],
        "numbers": [1, 2, 3, 42],
        "mixed": ["text", 123, True, None],
        "nested": {
            "inner": ["a", "b", "c"]
        }
    }
    
    # Test basic flattening
    assert FLATTEN(["strings"])(data) == "hello, world"
    assert FLATTEN(["numbers"])(data) == "1, 2, 3, 42" 
    assert FLATTEN(["mixed"])(data) == "text, 123, True"  # None is filtered out
    
    # Test custom delimiter
    assert FLATTEN(["strings"], delimiter=" + ")(data) == "hello + world"
    assert FLATTEN(["numbers"], delimiter=" | ")(data) == "1 | 2 | 3 | 42"
    
    # Test multiple paths
    assert FLATTEN(["strings", "numbers"], delimiter="; ")(data) == "hello; world; 1; 2; 3; 42"
    
    # Test nested path
    assert FLATTEN(["nested.inner"])(data) == "a, b, c"
    
    # Test with array notation - more complex scenario
    array_data = {
        "items": [
            {"values": [10, 20], "id": "A1"},
            {"values": [30, 40], "id": "B2"},
            {"values": [50, 60], "id": "C3"}
        ]
    }
    
    # Flatten values from first item
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
    
    # Basic coalesce and falsy value handling
    coalesce_cases = [
        (["null_value", "empty_string", "valid_string"], "found"),  # Skip None and empty string
        (["null_value", "zero"], 0),  # Zero is not considered empty
        (["null_value", "false"], False),  # False is not considered empty
        (["null_value", "empty_list"], []),  # Empty list is not considered empty
        (["null_value", "empty_dict"], {}),  # Empty dict is not considered empty
    ]
    
    for paths, expected in coalesce_cases:
        assert COALESCE(paths)(data) == expected
    
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
    
    # Test default value types and single path behavior
    default_cases = [
        (["missing"], None, None),  # None default
        (["missing"], 0, 0),  # Numeric default
        (["missing"], [], []),  # List default  
        (["missing"], {}, {}),  # Dict default
        (["valid_string"], None, "found"),  # Single valid path
        (["null_value"], "fallback", "fallback"),  # Single null path with fallback
    ]
    
    for paths, default, expected in default_cases:
        result = COALESCE(paths, default=default)(data)
        if expected is None:
            assert result is None
        else:
            assert result == expected
    
    # Test order matters
    order_data = {
        "first": "1st",
        "second": "2nd", 
        "third": "3rd"
    }
    
    # Should return first non-empty value found
    assert COALESCE(["first", "second", "third"])(order_data) == "1st"
    assert COALESCE(["second", "first", "third"])(order_data) == "2nd"
    
    # Test with array paths
    array_data = {
        "items": [None, "", "third_item"],
        "backup": "fallback_value"
    }
    
    assert COALESCE(["items[0]", "items[1]", "items[2]"])(array_data) == "third_item"
    assert COALESCE(["items[0]", "backup"])(array_data) == "fallback_value"
    
    # Test process method directly
    coalesce = COALESCE(["null_value", "valid_string"], default="fallback")
    assert coalesce.process(data) == "found"
    assert coalesce.process(data, context={"some": "context"}) == "found"
    
    # Test empty path list
    empty_coalesce = COALESCE([], default="empty_default")
    assert empty_coalesce(data) == "empty_default"
    
    # Test deeply nested paths
    deep_data = {
        "level1": {
            "level2": {
                "level3": {
                    "value": None
                }
            }
        },
        "fallback": "deep_fallback"
    }
    
    assert COALESCE(["level1.level2.level3.value", "fallback"])(deep_data) == "deep_fallback"


def test_split_seed():
    """Test SPLIT seed functionality from README."""
    data = {
        "full_name": "John-Doe-Smith",
        "email": "user@example.com"
    }
    
    # Test basic splitting
    split_fn = SPLIT("full_name", "-", 0)
    assert split_fn(data) == "John"
    
    # Test different indices
    assert SPLIT("full_name", "-", 1)(data) == "Doe"
    assert SPLIT("full_name", "-", 2)(data) == "Smith"
    
    # Test email splitting
    assert SPLIT("email", "@", 0)(data) == "user"
    assert SPLIT("email", "@", 1)(data) == "example.com"


def test_split_comprehensive():
    """Comprehensive tests for SPLIT behavior."""
    
    # Test data with various string patterns
    data = {
        "simple": "apple-banana-cherry",
        "spaces": "hello world",
        "csv": "name,age,city,country", 
        "path": "/home/user/file.txt",
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
    basic_split_cases = [
        ("simple", "-", 0, "apple"),
        ("simple", "-", 1, "banana"), 
        ("simple", "-", 2, "cherry"),
        ("spaces", " ", 1, "world"),
        ("csv", ",", 2, "city"),
        # Negative indexing
        ("simple", "-", -1, "cherry"),
        ("simple", "-", -2, "banana"),
        ("simple", "-", -3, "apple"),
        ("csv", ",", -1, "country"),
    ]
    
    for path, sep, index, expected in basic_split_cases:
        assert SPLIT(path, sep, index)(data) == expected
    
    # Path-like and empty parts splitting
    path_and_empty_cases = [
        ("path", "/", 1, "home"),
        ("path", "/", -1, "file.txt"),
        ("path", ".", -1, "txt"),  # File extension
        # Empty parts handling
        ("empty_parts", ",", 1, ""),
        ("empty_parts", ",", 3, ""),
        ("starts_with_sep", "-", 0, ""),
        ("ends_with_sep", "-", -1, ""),
    ]
    
    for path, sep, index, expected in path_and_empty_cases:
        assert SPLIT(path, sep, index)(data) == expected
    
    # Edge cases returning None or empty strings
    edge_cases = [
        ("single", "-", 0, "noSeparator"),  # No separator found
        ("single", "-", 1, None),  # Out of bounds
        ("empty_string", "-", 0, ""),  # Empty string
        ("empty_string", "-", 1, None),  # Empty string out of bounds
        ("none_value", "-", 0, None),  # None value
        ("simple", "-", 5, None),  # Out of bounds positive
        ("simple", "-", -5, None),  # Out of bounds negative
    ]
    
    for path, sep, index, expected in edge_cases:
        assert SPLIT(path, sep, index)(data) == expected
    
    # Edge case: non-string values should raise AttributeError
    try:
        SPLIT("number", "-", 0)(data)
        assert False, "Should have raised AttributeError"
    except AttributeError:
        pass
    
    # Multiple consecutive separators and unicode
    special_cases = [
        ("multiple_seps", "--", 0, "a"),
        ("multiple_seps", "--", 1, "b"),
        ("multiple_seps", "--", 2, "c"),
        ("unicode", "-", 0, "α"),
        ("unicode", "-", 1, "β"),
        ("unicode", "-", 2, "γ"),
        ("unicode", "-", 3, "δ"),
    ]
    
    for path, sep, index, expected in special_cases:
        assert SPLIT(path, sep, index)(data) == expected
    
    
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
    domain = SPLIT("email", "@", 1)(transform_data)
    assert domain == "example.com"
    
    # URL path extraction
    protocol = SPLIT("url", "://", 0)(transform_data)
    assert protocol == "https"
    
    # Test process method directly
    split_fn = SPLIT("simple", "-", 1)
    assert split_fn.process(data) == "banana"
    assert split_fn.process(data, context={"some": "context"}) == "banana"
    
    # Test with missing path
    missing_data = {"other": "value"}
    assert SPLIT("missing", "-", 0)(missing_data) is None
    
    # Test with deeply nested path
    nested_data = {
        "patient": {
            "name": {
                "full": "John-Michael-Doe"
            }
        }
    }
    
    assert SPLIT("patient.name.full", "-", 1)(nested_data) == "Michael"
    
    # Test with array notation
    array_data = {
        "names": ["Alice-Smith", "Bob-Jones", "Charlie-Brown"]
    }
    
    # Split first name
    assert SPLIT("names[0]", "-", 0)(array_data) == "Alice"
    assert SPLIT("names[0]", "-", 1)(array_data) == "Smith"
    
    # Split last name
    assert SPLIT("names[-1]", "-", 1)(array_data) == "Brown"
    
    # Real-world examples
    log_data = {
        "timestamp": "2023-12-01T10:30:45.123Z",
        "log_line": "ERROR [main] com.example.Service: Connection failed"
    }
    
    # Extract date from timestamp
    assert SPLIT("timestamp", "T", 0)(log_data) == "2023-12-01"
    
    # Extract log level
    assert SPLIT("log_line", " ", 0)(log_data) == "ERROR"
    
    # Extract class name from log line
    class_part = SPLIT("log_line", " ", 2)(log_data)  # "com.example.Service:"
    # Would need to do another split on the result, which is "com.example.Service:"
    assert class_part == "com.example.Service:"
    
    # File extension extraction
    file_data = {"filename": "document.backup.pdf"}
    assert SPLIT("filename", ".", -1)(file_data) == "pdf"
    assert SPLIT("filename", ".", 0)(file_data) == "document"