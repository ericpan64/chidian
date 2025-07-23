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

    # Test dict-like access with $ syntax
    assert table["$0"]["name"] == "John"
    assert table["$1"]["name"] == "Jane"
    assert table["$2"]["name"] == "Bob"


def test_dict_access_and_get():
    """Test built-in dict access and get method."""
    table = Table(
        [
            {"patient": {"id": "123", "name": "John"}, "status": "active"},
            {"patient": {"id": "456", "name": "Jane"}, "status": "inactive"},
            {"patient": {"id": "789", "name": "Bob"}, "status": "active"},
        ]
    )

    # Test built-in dict access (should work as normal dict)
    assert table["$0"]["patient"]["id"] == "123"
    assert table["$1"]["patient"]["id"] == "456"
    assert table["$2"]["patient"]["id"] == "789"

    # Test dict.get() method (inherited) - need to call super().get()
    assert dict.get(table, "$0")["patient"]["name"] == "John"
    assert dict.get(table, "$nonexistent") is None
    assert dict.get(table, "$nonexistent", "default") == "default"

    # Test Table.get method for extracting from all rows
    all_ids = table.get("patient.id")
    assert all_ids == ["123", "456", "789"]

    all_names = table.get("patient.name")
    assert all_names == ["John", "Jane", "Bob"]

    all_statuses = table.get("status")
    assert all_statuses == ["active", "inactive", "active"]

    # Test get with missing paths and defaults
    missing_field = table.get("missing_field", default="N/A")
    assert missing_field == ["N/A", "N/A", "N/A"]


def test_filter_method():
    """Test the filter method."""
    table = Table(
        [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False},
            {"name": "Bob", "age": 35, "active": True},
        ]
    )
    table.append({"name": "Alice", "age": 28, "active": True}, key="alice")

    # Filter by active status
    active_table = table.filter(lambda x: x.get("active", False))
    assert len(active_table) == 3

    # Check that new table has proper $ keys
    assert "$0" in active_table
    assert "$1" in active_table
    assert "$2" in active_table
    assert active_table["$0"]["name"] == "John"
    assert active_table["$1"]["name"] == "Bob"
    assert active_table["$2"]["name"] == "Alice"

    # Filter by age
    young_table = table.filter(lambda x: x.get("age", 0) < 30)
    assert len(young_table) == 2
    assert list(young_table)[0]["name"] == "Jane"
    assert list(young_table)[1]["name"] == "Alice"


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
    assert table["$0"]["name"] == "John"

    # Append with specific key (should get $ prefix)
    table.append({"name": "Jane"}, key="jane_key")
    assert table["$jane_key"]["name"] == "Jane"
    assert len(table) == 2

    # Append another auto-keyed row
    table.append({"name": "Bob"})
    assert table["$2"]["name"] == "Bob"
    assert len(table) == 3

    # Test accessing named row with dict access
    assert table["$jane_key"]["name"] == "Jane"


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


def test_complex_nested_access():
    """Test complex nested data access."""
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
            }
        ]
    )

    # Access nested array element using get
    mrn = table.get("patient.identifiers[0].value")
    assert mrn == ["MRN123"]

    # Access all encounter IDs using get
    encounter_ids = table.get("encounters[*].id")
    assert encounter_ids == [["e1", "e2"]]

    # Access using dict access
    first_patient_id = table["$0"]["patient"]["id"]
    assert first_patient_id == "123"

    # Test complex path with array using get
    all_identifiers = table.get("patient.identifiers")
    assert len(all_identifiers[0]) == 2
    assert all_identifiers[0][0]["system"] == "MRN"


def test_init_with_dict():
    """Test initialization with dict instead of list."""
    rows = {"user1": {"name": "John", "age": 30}, "user2": {"name": "Jane", "age": 25}}

    table = Table(rows)

    assert len(table) == 2
    assert "$user1" in table
    assert "$user2" in table
    assert table["$user1"]["name"] == "John"
    assert table["$user2"]["name"] == "Jane"


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
