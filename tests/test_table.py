from chidian.table import Table


def test_basic_table():
    """Test basic Table functionality."""
    # Create from list
    rows = [
        {"id": "p1", "name": "John", "age": 30},
        {"id": "p2", "name": "Jane", "age": 25},
        {"id": "p3", "name": "Bob", "age": 35},
    ]

    table = Table(rows)

    # Test length
    assert len(table) == 3

    # Test iteration
    assert list(table) == rows


def test_dict_indexing():
    """Test dict-like access with $ syntax."""
    table = Table(
        [
            {"id": "p1", "name": "John", "age": 30},
            {"id": "p2", "name": "Jane", "age": 25},
        ]
    )

    # Test basic dict access
    assert table["$0.name"] == "John"
    assert table["$1.name"] == "Jane"

    # Test __contains__ method
    assert "$0" in table
    assert "$1" in table
    assert "$nonexistent" not in table

    # Test with custom keys
    table.append({"name": "Bob", "age": 35}, custom_key="bob")
    assert table["$bob"]["name"] == "Bob"


def test_get_method_basic():
    """Test Table.get method for extracting values from all rows."""
    table = Table(
        [
            {"name": "John", "age": 30, "city": "NYC"},
            {"name": "Jane", "age": 25, "city": "LA"},
            {"name": "Bob", "age": 35},  # Note: no city
        ]
    )

    # Test simple field extraction
    assert table.get("name") == ["John", "Jane", "Bob"]
    assert table.get("age") == [30, 25, 35]

    # Test with missing fields and default
    assert table.get("city") == ["NYC", "LA", None]
    assert table.get("city", default="Unknown") == ["NYC", "LA", "Unknown"]

    # Test completely missing field
    assert table.get("phone") == [None, None, None]
    assert table.get("phone", default="N/A") == ["N/A", "N/A", "N/A"]


def test_get_method_nested():
    """Test Table.get method with nested paths."""
    table = Table(
        [
            {"patient": {"id": "123", "name": "John"}, "status": "active"},
            {"patient": {"id": "456", "name": "Jane"}, "status": "inactive"},
            {"patient": {"id": "789", "name": "Bob"}, "status": "active"},
        ]
    )

    # Test nested path extraction
    assert table.get("patient.id") == ["123", "456", "789"]
    assert table.get("patient.name") == ["John", "Jane", "Bob"]
    assert table.get("status") == ["active", "inactive", "active"]

    # Test missing nested paths
    assert table.get("patient.age") == [None, None, None]
    assert table.get("patient.age", default=0) == [0, 0, 0]

    # Test partially missing nested structure
    table_mixed = Table(
        [
            {"patient": {"id": "123", "name": "John"}},
            {"status": "active"},  # No patient object
            {"patient": {"id": "789"}},  # No name
        ]
    )
    assert table_mixed.get("patient.name") == ["John", None, None]
    assert table_mixed.get("patient.name", default="Unknown") == [
        "John",
        "Unknown",
        "Unknown",
    ]


def test_filter_method():
    """Test the filter method."""
    table = Table(
        [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False},
            {"name": "Bob", "age": 35, "active": True},
        ]
    )
    table.append({"name": "Alice", "age": 28, "active": True}, custom_key="alice")

    # Filter by active status
    active_table = table.filter(lambda x: x.get("active", False))
    assert len(active_table) == 3

    # Check that new table has proper $ keys
    assert "$0" in active_table
    assert "$1" in active_table
    assert "$2" in active_table
    assert active_table["$0.name"] == "John"
    assert active_table["$1.name"] == "Bob"
    assert active_table["$2.name"] == "Alice"

    # Filter by age
    young_table = table.filter(lambda x: x.get("age", 0) < 30)
    assert len(young_table) == 2
    assert young_table["$0.name"] == "Jane"
    assert young_table["$1.name"] == "Alice"


def test_map_method():
    """Test the map method."""
    table = Table([{"name": "John", "age": 30}, {"name": "Jane", "age": 25}])

    # Transform to add computed field
    enhanced = table.map(lambda x: {**x, "adult": x.get("age", 0) >= 18})

    assert all("adult" in row for row in enhanced)
    assert all(row["adult"] is True for row in enhanced)


def test_columns_property():
    """Test the columns property."""
    table = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane", "city": "NYC"},
            {"id": "123", "name": "Bob", "age": 25, "country": "USA"},
        ]
    )

    expected_columns = {"name", "age", "city", "id", "country"}
    assert table.columns == expected_columns


def test_to_list_to_dict():
    """Test conversion methods."""
    rows = [{"id": 1, "name": "Test"}, {"id": 2, "name": "Another"}]
    table = Table(rows)

    # Test to_list
    assert table.to_list() == rows

    # Test to_dict
    result_dict = table.to_dict()
    assert "$0" in result_dict
    assert "$1" in result_dict
    assert result_dict["$0"] == {"id": 1, "name": "Test"}
    assert result_dict["$1"] == {"id": 2, "name": "Another"}


def test_append_method():
    """Test appending rows to table."""
    table = Table()

    # Append with auto-generated key
    table.append({"name": "John"})
    assert len(table) == 1
    assert table["$0.name"] == "John"

    # Append with specific key (should get $ prefix)
    table.append({"name": "Jane"}, custom_key="jane_key")
    assert table["$jane_key.name"] == "Jane"
    assert len(table) == 2

    # Append another auto-keyed row
    table.append({"name": "Bob"})
    assert table["$2.name"] == "Bob"
    assert len(table) == 3

    # Test accessing named row with dict access
    assert table["$jane_key.name"] == "Jane"


def test_unique_method():
    """Test unique values extraction."""
    table = Table(
        [
            {"name": "John", "city": "NYC"},
            {"name": "Jane", "city": "LA"},
            {"name": "Bob", "city": "NYC"},
            {"name": "Alice", "city": "Chicago"},
            {"name": "Charlie", "city": "NYC"},
        ]
    )

    unique_cities = table.unique("city")
    assert set(unique_cities) == {"NYC", "LA", "Chicago"}
    assert len(unique_cities) == 3  # Should preserve order and uniqueness

    unique_names = table.unique("name")
    assert len(unique_names) == 5  # All names are unique


def test_group_by_method():
    """Test grouping by a column."""
    table = Table(
        [
            {"name": "John", "city": "NYC", "age": 30},
            {"name": "Jane", "city": "LA", "age": 25},
            {"name": "Bob", "city": "NYC", "age": 35},
            {"name": "Alice", "city": "Chicago", "age": 28},
            {"name": "Charlie", "city": "NYC", "age": 40},
        ]
    )

    grouped = table.group_by("city")

    assert "NYC" in grouped
    assert "LA" in grouped
    assert "Chicago" in grouped

    nyc_table = grouped["NYC"]
    assert len(nyc_table) == 3
    assert nyc_table.get("name") == ["John", "Bob", "Charlie"]

    la_table = grouped["LA"]
    assert len(la_table) == 1
    assert la_table.get("name") == ["Jane"]

    chicago_table = grouped["Chicago"]
    assert len(chicago_table) == 1
    assert chicago_table.get("name") == ["Alice"]


def test_head_tail_methods():
    """Test head and tail methods."""
    table = Table([{"id": i, "name": f"Person{i}"} for i in range(10)])

    # Test head
    head_3 = table.head(3)
    assert len(head_3) == 3
    assert head_3.get("id") == [0, 1, 2]

    head_default = table.head()
    assert len(head_default) == 5  # Default is 5
    assert head_default.get("id") == [0, 1, 2, 3, 4]

    # Test tail
    tail_3 = table.tail(3)
    assert len(tail_3) == 3
    assert tail_3.get("id") == [7, 8, 9]

    tail_default = table.tail()
    assert len(tail_default) == 5  # Default is 5
    assert tail_default.get("id") == [5, 6, 7, 8, 9]


def test_get_method_arrays():
    """Test Table.get method with array paths and wildcards."""
    table = Table(
        [
            {
                "patient": {
                    "id": "123",
                    "identifiers": [
                        {"system": "MRN", "value": "MRN123"},
                        {"system": "SSN", "value": "SSN456"},
                    ],
                },
                "encounters": [
                    {"id": "e1", "date": "2024-01-01"},
                    {"id": "e2", "date": "2024-02-01"},
                ],
            },
            {
                "patient": {
                    "id": "456",
                    "identifiers": [
                        {"system": "MRN", "value": "MRN789"},
                    ],
                },
                "encounters": [],  # Empty encounters
            },
        ]
    )

    # Test array index access
    assert table.get("patient.identifiers[0].value") == ["MRN123", "MRN789"]
    assert table.get("patient.identifiers[1].value") == ["SSN456", None]

    # Test wildcard array access
    assert table.get("encounters[*].id") == [["e1", "e2"], []]
    # Note: When wildcard matches single item, it returns the item directly, not wrapped in a list
    assert table.get("patient.identifiers[*].system") == [["MRN", "SSN"], "MRN"]

    # Test getting entire array
    identifiers = table.get("patient.identifiers")
    assert len(identifiers) == 2
    assert len(identifiers[0]) == 2  # First patient has 2 identifiers
    assert len(identifiers[1]) == 1  # Second patient has 1 identifier

    # Test with missing array paths
    assert table.get("patient.addresses[0].city") == [None, None]
    assert table.get("patient.addresses[0].city", default="Unknown") == [
        "Unknown",
        "Unknown",
    ]


def test_get_method_dollar_syntax():
    """Test Table.get method with $-prefixed paths for specific row access."""
    table = Table(
        [
            {"name": "John", "age": 30, "city": "NYC"},
            {"name": "Jane", "age": 25, "city": "LA"},
            {"name": "Bob", "age": 35},  # Note: no city
        ]
    )

    # Test basic $-prefixed access
    assert table.get("$0.name") == "John"
    assert table.get("$1.age") == 25
    assert table.get("$2.name") == "Bob"

    # Test missing fields with $-prefix
    assert table.get("$2.city") is None
    assert table.get("$2.city", default="Unknown") == "Unknown"

    # Test non-existent row keys
    assert table.get("$99.name") is None
    assert table.get("$99.name", default="N/A") == "N/A"

    # Test getting entire row with just $key
    row0 = table.get("$0")
    assert row0 == {"name": "John", "age": 30, "city": "NYC"}

    # Test with custom keys
    table.append({"name": "Alice", "age": 28}, custom_key="alice")
    assert table.get("$alice.name") == "Alice"
    assert table.get("$alice.age") == 28

    # Test nested paths with $-prefix
    table2 = Table(
        [
            {"patient": {"id": "123", "name": "John"}},
            {"patient": {"id": "456", "name": "Jane"}},
        ]
    )
    assert table2.get("$0.patient.id") == "123"
    assert table2.get("$1.patient.name") == "Jane"

    # Compare with non-$ behavior (returns list)
    assert table.get("name") == ["John", "Jane", "Bob", "Alice"]
    assert table2.get("patient.id") == ["123", "456"]


def test_get_method_edge_cases():
    """Test Table.get method edge cases."""
    # Test with empty table
    empty_table = Table()
    assert empty_table.get("name") == []
    assert empty_table.get("name", default="N/A") == []

    # Test with heterogeneous data types
    table = Table(
        [
            {"value": "string"},
            {"value": 123},
            {"value": True},
            {"value": None},
            {"value": [1, 2, 3]},
            {"value": {"nested": "object"}},
        ]
    )

    values = table.get("value")
    assert values == ["string", 123, True, None, [1, 2, 3], {"nested": "object"}]

    # Test deep nesting with mixed types
    table2 = Table(
        [
            {"data": {"level1": {"level2": {"level3": "deep"}}}},
            {"data": {"level1": "shallow"}},  # Not nested as deep
            {"data": None},  # Null data
            {},  # Missing data entirely
        ]
    )

    assert table2.get("data.level1.level2.level3") == ["deep", None, None, None]
    assert table2.get("data.level1") == [
        {"level2": {"level3": "deep"}},
        "shallow",
        None,
        None,
    ]


def test_init_with_dict():
    """Test initialization with dict instead of list."""
    rows = {"user1": {"name": "John", "age": 30}, "user2": {"name": "Jane", "age": 25}}

    table = Table(rows)

    assert len(table) == 2
    assert "$user1" in table
    assert "$user2" in table
    assert table["$user1.name"] == "John"
    assert table["$user2.name"] == "Jane"


def test_empty_table():
    """Test empty table initialization."""
    table = Table()

    assert len(table) == 0
    assert table.columns == set()
    assert table.to_list() == []
    assert table.to_dict() == {}


# DSL Tests (TDD - these will fail until DSL is implemented)


def test_select_dsl_basic():
    """Test basic select DSL functionality."""
    table = Table(
        [
            {"name": "John", "age": 30, "city": "NYC"},
            {"name": "Jane", "age": 25, "city": "LA"},
        ]
    )

    # Test specific column selection
    result = table.select("name, age")
    assert len(result) == 2
    assert result.get("name") == ["John", "Jane"]
    assert result.get("age") == [30, 25]
    assert "city" not in result.columns

    # Test wildcard selection
    result = table.select("*")
    assert len(result) == 2
    assert result.columns == {"name", "age", "city"}


def test_select_dsl_with_renaming():
    """Test select DSL with column renaming."""
    table = Table(
        [
            {"patient": {"id": "123", "name": "John"}},
            {"patient": {"id": "456", "name": "Jane"}},
        ]
    )

    # Test column renaming
    result = table.select("patient.id -> patient_id, patient.name -> patient_name")
    assert len(result) == 2
    assert result.get("patient_id") == ["123", "456"]
    assert result.get("patient_name") == ["John", "Jane"]
    assert result.columns == {"patient_id", "patient_name"}


def test_filter_dsl_basic():
    """Test basic filter DSL functionality."""
    table = Table(
        [
            {"name": "John", "age": 30},
            {"name": "Jane", "age": 25},
            {"name": "Bob", "age": 35},
        ]
    )

    # Test numeric comparison
    result = table.filter("age > 26")
    assert len(result) == 2
    assert result.get("name") == ["John", "Bob"]

    # Test string equality
    result = table.filter("name = 'John'")
    assert len(result) == 1
    assert result.get("name") == ["John"]


def test_filter_dsl_complex():
    """Test complex filter DSL functionality."""
    table = Table(
        [
            {"name": "John", "age": 30, "status": "active"},
            {"name": "Jane", "age": 25, "status": "inactive"},
            {"name": "Bob", "age": 35, "status": "active"},
        ]
    )

    # Test AND operator
    result = table.filter("status = 'active' AND age >= 30")
    assert len(result) == 2
    assert result.get("name") == ["John", "Bob"]

    # Test OR operator
    result = table.filter("age > 25 OR name = 'Jane'")
    assert len(result) == 3  # All rows match


def test_filter_dsl_nested_paths():
    """Test filter DSL with nested paths."""
    table = Table(
        [
            {"patient": {"name": "John", "addresses": [{"city": "NYC"}]}},
            {"patient": {"name": "Jane", "addresses": [{"city": "LA"}]}},
        ]
    )

    # Test nested path with array index
    result = table.filter("patient.addresses[0].city = 'NYC'")
    assert len(result) == 1
    assert result.get("patient.name") == ["John"]

    # Test CONTAINS with wildcard - note: this returns list from wildcard
    table2 = Table(
        [
            {"name": "John", "cities": ["NYC", "Boston"]},
            {"name": "Jane", "cities": ["LA", "SF"]},
        ]
    )
    result = table2.filter("cities CONTAINS 'NYC'")
    assert len(result) == 1
    assert result.get("name") == ["John"]


# Integration tests showing expected DSL behavior (will pass once implemented)


def test_full_workflow_with_dsl():
    """Test complete workflow combining functional and DSL APIs."""
    table = Table(
        [
            {"name": "John", "age": 30, "city": "NYC", "department": "Engineering"},
            {"name": "Jane", "age": 25, "city": "LA", "department": "Marketing"},
            {"name": "Bob", "age": 35, "city": "NYC", "department": "Engineering"},
            {"name": "Alice", "age": 28, "city": "Chicago", "department": "Sales"},
        ]
    )

    # This workflow combines DSL and functional APIs:
    # 1. Filter for NYC employees over 25
    # 2. Select specific columns with renaming
    # 3. Add computed field
    # 4. Get unique departments

    # Step 1: DSL filter
    nyc_employees = table.filter("city = 'NYC' AND age > 25")
    assert len(nyc_employees) == 2

    # Step 2: DSL select
    selected = nyc_employees.select("name -> employee_name, department, age")
    assert len(selected) == 2
    assert selected.columns == {"employee_name", "department", "age"}
    assert selected.get("employee_name") == ["John", "Bob"]

    # Step 3: Functional map
    enhanced = selected.map(
        lambda row: {**row, "seniority": "Senior" if row["age"] > 30 else "Junior"}
    )
    assert len(enhanced) == 2

    # Step 4: Functional unique
    departments = enhanced.unique("department")
    assert departments == ["Engineering"]  # Both NYC employees are in Engineering
