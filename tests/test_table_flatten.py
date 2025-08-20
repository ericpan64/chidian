"""Tests for Table flattening functionality."""

from chidian.table import Table


def test_basic_flattening():
    """Test basic dict/list flattening functionality."""
    # Test the canonical example: {'a': 1, 'b': [2], 'c': {'d': 3}}
    t = Table([{"a": 1, "b": [2], "c": {"d": 3}}])
    flattened = t.flatten()

    # Should have flattened structure
    assert len(flattened) == 1
    row = flattened.to_list()[0]

    expected_keys = {"a", "b[0]", "c.d"}
    assert set(row.keys()) == expected_keys
    assert row["a"] == 1
    assert row["b[0]"] == 2
    assert row["c.d"] == 3


def test_columns_flattened():
    """Test columns_flattened method for column preview."""
    t = Table([{"a": 1, "b": [1, 2]}, {"a": 2, "b": [3], "c": {"d": 4}}])

    # Should get union of all flattened columns
    columns = t.columns_flattened()
    expected = {"a", "b[0]", "b[1]", "c.d"}
    assert columns == expected

    # Test sampling
    columns_sample = t.columns_flattened(sample_rows=1)
    expected_sample = {"a", "b[0]", "b[1]"}  # Only first row
    assert columns_sample == expected_sample


def test_ragged_arrays():
    """Test arrays of different lengths across rows."""
    t = Table([{"items": [1, 2, 3]}, {"items": [4]}, {"items": [5, 6]}])

    flattened = t.flatten()
    columns = flattened.columns

    # Should have columns for all indices that appear
    expected_columns = {"items[0]", "items[1]", "items[2]"}
    assert columns == expected_columns

    rows = flattened.to_list()
    # First row has all values
    assert rows[0]["items[0]"] == 1
    assert rows[0]["items[1]"] == 2
    assert rows[0]["items[2]"] == 3

    # Second row only has first value, others should be missing
    assert rows[1]["items[0]"] == 4
    assert "items[1]" not in rows[1]
    assert "items[2]" not in rows[1]

    # Third row has first two values
    assert rows[2]["items[0]"] == 5
    assert rows[2]["items[1]"] == 6
    assert "items[2]" not in rows[2]


def test_mixed_types():
    """Test same key as different types across rows."""
    t = Table(
        [
            {"data": {"nested": "value1"}},
            {"data": "simple_string"},
            {"data": {"nested": "value2", "other": 42}},
        ]
    )

    flattened = t.flatten()
    columns = flattened.columns

    # Should include both direct 'data' and nested 'data.nested', 'data.other'
    expected_columns = {"data", "data.nested", "data.other"}
    assert columns == expected_columns

    rows = flattened.to_list()

    # First row: only nested structure
    assert "data" not in rows[0]  # No direct 'data' value
    assert rows[0]["data.nested"] == "value1"
    assert "data.other" not in rows[0]

    # Second row: only direct value
    assert rows[1]["data"] == "simple_string"
    assert "data.nested" not in rows[1]
    assert "data.other" not in rows[1]

    # Third row: nested structure with multiple keys
    assert "data" not in rows[2]
    assert rows[2]["data.nested"] == "value2"
    assert rows[2]["data.other"] == 42


def test_special_keys():
    """Test keys with special characters that need bracket notation."""
    t = Table(
        [
            {
                "normal_key": 1,
                "key.with.dots": 2,
                "key with spaces": 3,
                "key[with]brackets": 4,
                'key"with"quotes': 5,
                "nested": {"normal": "a", "special.key": "b"},
            }
        ]
    )

    flattened = t.flatten()
    columns = flattened.columns

    # Check that special keys are properly encoded
    assert "normal_key" in columns
    assert '["key.with.dots"]' in columns
    assert '["key with spaces"]' in columns
    assert '["key[with]brackets"]' in columns
    assert '["key\\"with\\"quotes"]' in columns
    assert "nested.normal" in columns
    assert 'nested.["special.key"]' in columns

    row = flattened.to_list()[0]
    assert row["normal_key"] == 1
    assert row['["key.with.dots"]'] == 2
    assert row['["key with spaces"]'] == 3
    assert row['["key[with]brackets"]'] == 4
    assert row['["key\\"with\\"quotes"]'] == 5
    assert row["nested.normal"] == "a"
    assert row['nested.["special.key"]'] == "b"


def test_max_depth_limit():
    """Test depth limiting functionality."""
    deep_data = {"level1": {"level2": {"level3": {"level4": "deep_value"}}}}

    t = Table([deep_data])

    # No depth limit - should fully flatten
    unlimited = t.flatten()
    assert "level1.level2.level3.level4" in unlimited.columns
    assert unlimited.to_list()[0]["level1.level2.level3.level4"] == "deep_value"

    # Depth limit of 2 - should stop at level3 (depth 0,1,2)
    limited = t.flatten(max_depth=2)
    columns = limited.columns
    assert "level1.level2.level3" in columns
    assert "level1.level2.level3.level4" not in columns

    # The limited value should contain the remaining nested structure
    row = limited.to_list()[0]
    remaining = row["level1.level2.level3"]
    assert remaining == {"level4": "deep_value"}


def test_array_index_limit():
    """Test array index limiting functionality."""
    t = Table([{"items": list(range(10))}])  # 0 through 9

    # No limit - should include all indices
    unlimited = t.flatten()
    for i in range(10):
        assert f"items[{i}]" in unlimited.columns

    # Limit to 3 - should only include 0, 1, 2
    limited = t.flatten(array_index_limit=3)
    columns = limited.columns
    expected_columns = {"items[0]", "items[1]", "items[2]"}
    assert columns == expected_columns

    row = limited.to_list()[0]
    assert row["items[0]"] == 0
    assert row["items[1]"] == 1
    assert row["items[2]"] == 2
    # Should not have items[3] and beyond


def test_get_path_value_compatibility():
    """Test that _get_path_value works with flattened tables."""
    original = Table([{"user": {"name": "John", "prefs": ["email", "sms"]}, "id": 123}])

    flattened = original.flatten()

    # Test that path-based access works on flattened table
    # Should be able to access flattened keys directly
    row = flattened.to_list()[0]
    table_instance = flattened

    # Direct key access should work
    assert table_instance._get_path_value(row, "user.name") == "John"
    assert table_instance._get_path_value(row, "user.prefs[0]") == "email"
    assert table_instance._get_path_value(row, "user.prefs[1]") == "sms"
    assert table_instance._get_path_value(row, "id") == 123

    # Test that regular table operations work
    assert flattened.get("user.name") == ["John"]
    assert flattened.get("user.prefs[0]") == ["email"]


def test_join_on_flattened_path():
    """Test that joins work with flattened path columns."""
    table1 = Table(
        [{"user": {"id": 1}, "name": "John"}, {"user": {"id": 2}, "name": "Jane"}]
    )

    table2 = Table([{"user": {"id": 1}, "score": 85}, {"user": {"id": 2}, "score": 92}])

    # Flatten both tables
    flat1 = table1.flatten()
    flat2 = table2.flatten()

    # Should be able to join on the flattened path
    joined = flat1.join(flat2, on="user.id")

    assert len(joined) == 2
    rows = joined.to_list()

    # Verify join worked correctly
    assert rows[0]["name"] == "John"
    assert rows[0]["score"] == 85
    assert rows[1]["name"] == "Jane"
    assert rows[1]["score"] == 92


def test_select_on_flattened():
    """Test select operations on flattened tables."""
    original = Table(
        [
            {
                "user": {"name": "John", "age": 30},
                "meta": {"created": "2023-01-01"},
                "id": 123,
            }
        ]
    )

    flattened = original.flatten()

    # Select specific flattened columns (avoiding bracket notation which select parser doesn't support yet)
    selected = flattened.select("user.name, user.age, meta.created")

    assert len(selected) == 1
    row = selected.to_list()[0]
    assert set(row.keys()) == {"name", "age", "created"}  # Renamed from paths
    assert row["name"] == "John"
    assert row["age"] == 30
    assert row["created"] == "2023-01-01"


def test_group_by_on_flattened():
    """Test group_by operations on flattened tables."""
    original = Table(
        [
            {"user": {"dept": "eng"}, "name": "John"},
            {"user": {"dept": "eng"}, "name": "Jane"},
            {"user": {"dept": "sales"}, "name": "Bob"},
        ]
    )

    flattened = original.flatten()

    # Group by flattened path
    groups = flattened.group_by("user.dept")

    assert len(groups) == 2
    assert "eng" in groups
    assert "sales" in groups

    eng_group = groups["eng"]
    assert len(eng_group) == 2

    sales_group = groups["sales"]
    assert len(sales_group) == 1


def test_display_flattened():
    """Test show method with flatten=True."""
    nested = Table(
        [
            {
                "user": {"name": "John", "prefs": ["email", "sms"]},
                "meta": {"created": "2023-01-01"},
            }
        ]
    )

    # Regular display
    regular_display = nested.show()
    assert "user" in regular_display
    assert "user.name" not in regular_display

    # Flattened display
    flat_display = nested.show(flatten=True)
    assert "user.name" in flat_display
    assert "user.prefs[0]" in flat_display
    assert "user.prefs[1]" in flat_display
    assert "meta.created" in flat_display
    assert "John" in flat_display
    assert "email" in flat_display


def test_to_pandas_flatten():
    """Test pandas export with flattening."""
    try:
        import pandas as pd  # noqa: F401
    except ImportError:
        # Skip if pandas not available
        return

    nested = Table([{"user": {"name": "John", "age": 30}, "tags": ["python", "data"]}])

    # Export with flattening
    df = nested.to_pandas(flatten=True)

    expected_columns = {"user.name", "user.age", "tags[0]", "tags[1]"}
    assert set(df.columns) == expected_columns

    assert df.iloc[0]["user.name"] == "John"
    assert df.iloc[0]["user.age"] == 30
    assert df.iloc[0]["tags[0]"] == "python"
    assert df.iloc[0]["tags[1]"] == "data"


def test_to_polars_flatten():
    """Test polars export with flattening."""
    try:
        import polars as pl  # noqa: F401
    except ImportError:
        # Skip if polars not available
        return

    nested = Table([{"user": {"name": "John", "age": 30}, "tags": ["python", "data"]}])

    # Export with flattening
    df = nested.to_polars(flatten=True)

    expected_columns = {"user.name", "user.age", "tags[0]", "tags[1]"}
    assert set(df.columns) == expected_columns

    row_dict = df.to_dicts()[0]
    assert row_dict["user.name"] == "John"
    assert row_dict["user.age"] == 30
    assert row_dict["tags[0]"] == "python"
    assert row_dict["tags[1]"] == "data"


def test_to_csv_flatten():
    """Test CSV export with flattening."""
    import csv
    import tempfile

    nested = Table([{"user": {"name": "John", "age": 30}, "tags": ["python", "data"]}])

    # Export with flattening
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        nested.to_csv(f.name, flatten=True)

    # Read back and verify
    with open(f.name, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]

    assert row["user.name"] == "John"
    assert row["user.age"] == "30"
    assert row["tags[0]"] == "python"
    assert row["tags[1]"] == "data"


def test_empty_table_flatten():
    """Test flattening empty table."""
    empty = Table()
    flattened = empty.flatten()

    assert len(flattened) == 0
    assert flattened.columns == set()
    assert flattened.columns_flattened() == set()


def test_none_values_flatten():
    """Test flattening with None values."""
    t = Table([{"data": None, "nested": {"value": None}, "array": [None, 1, None]}])

    flattened = t.flatten()
    row = flattened.to_list()[0]

    assert row["data"] is None
    assert row["nested.value"] is None
    assert row["array[0]"] is None
    assert row["array[1]"] == 1
    assert row["array[2]"] is None


def test_complex_nested_structure():
    """Test flattening deeply nested and complex structures."""
    complex_data = {
        "users": [
            {
                "profile": {"name": "John", "settings": {"theme": "dark"}},
                "contacts": [{"type": "email", "value": "john@example.com"}],
            },
            {
                "profile": {"name": "Jane", "settings": {"theme": "light"}},
                "contacts": [
                    {"type": "email", "value": "jane@example.com"},
                    {"type": "phone", "value": "555-1234"},
                ],
            },
        ],
        "meta": {"version": 1},
    }

    t = Table([complex_data])
    flattened = t.flatten()

    columns = flattened.columns

    # Should have all the deeply nested paths
    assert "users[0].profile.name" in columns
    assert "users[0].profile.settings.theme" in columns
    assert "users[0].contacts[0].type" in columns
    assert "users[0].contacts[0].value" in columns
    assert "users[1].profile.name" in columns
    assert "users[1].contacts[1].type" in columns
    assert "meta.version" in columns

    row = flattened.to_list()[0]
    assert row["users[0].profile.name"] == "John"
    assert row["users[0].profile.settings.theme"] == "dark"
    assert row["users[1].contacts[1].value"] == "555-1234"
    assert row["meta.version"] == 1
