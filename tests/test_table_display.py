"""Tests for Table display methods."""

from chidian.table import Table


def test_repr():
    """Test __repr__ method."""
    # Empty table
    t = Table()
    assert repr(t) == "<Table: 0 rows × 0 columns>"

    # Single row, single column
    t = Table([{"name": "John"}])
    assert repr(t) == "<Table: 1 row × 1 column>"

    # Multiple rows and columns
    t = Table([{"name": "John", "age": 30}, {"name": "Jane", "age": 25}])
    assert repr(t) == "<Table: 2 rows × 2 columns>"

    # Sparse table (different columns per row)
    t = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane", "city": "NYC"},
            {"email": "bob@example.com"},
        ]
    )
    assert repr(t) == "<Table: 3 rows × 4 columns>"


def test_str_basic():
    """Test __str__ method with basic data."""
    t = Table([{"name": "John", "age": 30}, {"name": "Jane", "age": 25}])

    result = str(t)
    assert "$key" in result
    assert "name" in result
    assert "age" in result
    assert "John" in result
    assert "Jane" in result
    assert "30" in result
    assert "25" in result
    assert "$0" in result
    assert "$1" in result


def test_str_empty():
    """Test __str__ with empty table."""
    t = Table()
    assert str(t) == "<Empty Table>"


def test_str_truncation():
    """Test that __str__ shows only first 5 rows by default."""
    rows = [{"id": i, "value": f"item{i}"} for i in range(10)]
    t = Table(rows)

    result = str(t)
    # Should show first 5 rows
    assert "$0" in result
    assert "$4" in result
    # Should not show row 5 and beyond in the data
    assert "$5" not in result
    # Should show indicator for more rows
    assert "5 more rows" in result


def test_show_method():
    """Test show() method with various parameters."""
    rows = [
        {"id": i, "description": f"A very long description for item {i}" * 3}
        for i in range(10)
    ]
    t = Table(rows)

    # Show only 2 rows
    result = t.show(n=2)
    assert "$0" in result
    assert "$1" in result
    assert "$2" not in result
    assert "8 more rows" in result

    # Show all rows
    result = t.show(n=20)
    assert "$0" in result
    assert "$9" in result
    assert "more row" not in result

    # Test truncation
    result = t.show(n=1, truncate=20)
    assert "..." in result  # Description should be truncated


def test_show_with_none_values():
    """Test display of None values."""
    t = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": None},
            {"name": None, "age": 25},
        ]
    )

    result = str(t)
    assert "None" in result


def test_show_with_nested_data():
    """Test display of nested structures."""
    t = Table(
        [
            {"name": "John", "data": {"age": 30, "city": "NYC"}},
            {"name": "Jane", "data": [1, 2, 3]},
        ]
    )

    result = str(t)
    # Should show JSON representation
    assert '{"age":30' in result or '"city"' in result
    assert "[1,2,3]" in result


def test_show_with_custom_keys():
    """Test display with custom row keys."""
    t = Table()
    t.append({"name": "Alice"}, custom_key="alice")
    t.append({"name": "Bob"}, custom_key="bob")

    result = str(t)
    assert "$alice" in result
    assert "$bob" in result
    assert "Alice" in result
    assert "Bob" in result


def test_show_column_width():
    """Test that columns are properly aligned."""
    t = Table(
        [
            {"short": "a", "medium": "hello", "long": "this is a longer value"},
            {"short": "bb", "medium": "world", "long": "another long value"},
        ]
    )

    result = str(t)
    lines = result.split("\n")

    # Check that separator line exists
    assert any("-+-" in line for line in lines)

    # Check that all data lines have consistent structure
    data_lines = [line for line in lines if "|" in line]
    assert len(data_lines) >= 3  # Header + 2 data rows
