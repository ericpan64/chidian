"""Tests for Table pandas interoperability."""

import pytest

from chidian.table import Table

pd = pytest.importorskip("pandas")


def test_to_pandas_basic():
    """Test basic conversion to pandas DataFrame."""
    t = Table([{"a": 1}, {"b": 2}])
    df = t.to_pandas()
    assert set(df.columns) >= {"a", "b"}
    assert len(df) == 2


def test_to_pandas_index():
    """Test conversion with index from row keys."""
    t = Table([{"a": 1}, {"a": 2}])
    df = t.to_pandas(index=True)
    assert df.index.name == "_index"
    assert len(df) == 2
    # Check that index values are correct (stripped of $)
    assert list(df.index) == ["0", "1"]


def test_to_pandas_custom_index_name():
    """Test conversion with custom index name."""
    t = Table([{"value": 10}, {"value": 20}])
    df = t.to_pandas(index=True, index_name="row_id")
    assert df.index.name == "row_id"
    assert len(df) == 2


def test_to_pandas_with_custom_keys():
    """Test conversion with custom row keys."""
    t = Table()
    t.append({"name": "Alice", "age": 30}, custom_key="alice")
    t.append({"name": "Bob", "age": 25}, custom_key="bob")

    df = t.to_pandas(index=True)
    assert df.index.name == "_index"
    assert list(df.index) == ["alice", "bob"]
    assert list(df["name"]) == ["Alice", "Bob"]
    assert list(df["age"]) == [30, 25]


def test_to_pandas_sparse_data():
    """Test conversion with sparse/missing data."""
    t = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane"},  # Missing age
            {"age": 25},  # Missing name
        ]
    )

    df = t.to_pandas()
    assert len(df) == 3
    assert pd.isna(df.iloc[1]["age"])
    assert pd.isna(df.iloc[2]["name"])


def test_to_pandas_empty_table():
    """Test conversion of empty table."""
    t = Table()
    df = t.to_pandas()
    assert len(df) == 0
    assert list(df.columns) == []


def test_to_pandas_nested_data():
    """Test conversion with nested structures."""
    t = Table(
        [
            {"id": 1, "metadata": {"color": "red", "size": "large"}},
            {"id": 2, "metadata": {"color": "blue", "size": "small"}},
        ]
    )

    df = t.to_pandas()
    assert len(df) == 2
    # Nested dicts should be preserved as-is
    assert isinstance(df.iloc[0]["metadata"], dict)
    assert df.iloc[0]["metadata"]["color"] == "red"
