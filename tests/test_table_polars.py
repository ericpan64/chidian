"""Tests for Table polars interoperability."""

import pytest

from chidian.table import Table

pl = pytest.importorskip("polars")


def test_to_polars_basic():
    """Test basic conversion to polars DataFrame."""
    t = Table([{"a": 1}, {"b": 2}])
    df = t.to_polars()
    assert set(df.columns) >= {"a", "b"}
    assert df.height == 2


def test_to_polars_add_index():
    """Test conversion with index column from row keys."""
    t = Table([{"a": 1}, {"a": 2}])
    df = t.to_polars(add_index=True)
    assert "_index" in df.columns
    assert df.height == 2
    # Check that index values are correct (stripped of $)
    assert df["_index"].to_list() == ["0", "1"]


def test_to_polars_custom_index_name():
    """Test conversion with custom index column name."""
    t = Table([{"value": 10}, {"value": 20}])
    df = t.to_polars(add_index=True, index_name="row_id")
    assert "row_id" in df.columns
    assert df.height == 2


def test_to_polars_with_custom_keys():
    """Test conversion with custom row keys."""
    t = Table()
    t.append({"name": "Alice", "age": 30}, custom_key="alice")
    t.append({"name": "Bob", "age": 25}, custom_key="bob")

    df = t.to_polars(add_index=True)
    assert "_index" in df.columns
    assert df["_index"].to_list() == ["alice", "bob"]
    assert df["name"].to_list() == ["Alice", "Bob"]
    assert df["age"].to_list() == [30, 25]


def test_to_polars_sparse_data():
    """Test conversion with sparse/missing data."""
    t = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane"},  # Missing age
            {"age": 25},  # Missing name
        ]
    )

    df = t.to_polars()
    assert df.height == 3
    assert df["age"][1] is None
    assert df["name"][2] is None


def test_to_polars_empty_table():
    """Test conversion of empty table."""
    t = Table()
    df = t.to_polars()
    assert df.height == 0
    assert list(df.columns) == []


def test_to_polars_nested_data():
    """Test conversion with nested structures."""
    t = Table(
        [
            {"id": 1, "metadata": {"color": "red", "size": "large"}},
            {"id": 2, "metadata": {"color": "blue", "size": "small"}},
        ]
    )

    df = t.to_polars()
    assert df.height == 2
    # Nested dicts should be preserved as struct type
    metadata_values = df["metadata"].to_list()
    assert isinstance(metadata_values[0], dict)
    assert metadata_values[0]["color"] == "red"


def test_to_polars_no_index_by_default():
    """Test that index is not added by default."""
    t = Table([{"x": 1}, {"x": 2}, {"x": 3}])
    df = t.to_polars()
    assert "_index" not in df.columns
    assert list(df.columns) == ["x"]
