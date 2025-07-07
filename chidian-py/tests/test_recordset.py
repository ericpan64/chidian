from chidian.recordset import RecordSet


def test_basic_collection():
    """Test basic RecordSet functionality."""
    # Create from list
    items = [
        {"id": "p1", "name": "John", "age": 30},
        {"id": "p2", "name": "Jane", "age": 25},
        {"id": "p3", "name": "Bob", "age": 35},
    ]

    collection = RecordSet(items)

    # Test length
    assert len(collection) == 3

    # Test iteration
    assert list(collection) == items

    # Test dict-like access with new $ syntax
    assert collection["$0"]["name"] == "John"
    assert collection["$1"]["name"] == "Jane"
    assert collection["$2"]["name"] == "Bob"


def test_dict_access_and_get_all():
    """Test built-in dict access and get_all method."""
    collection = RecordSet(
        [
            {"patient": {"id": "123", "name": "John"}, "status": "active"},
            {"patient": {"id": "456", "name": "Jane"}, "status": "inactive"},
            {"patient": {"id": "789", "name": "Bob"}, "status": "active"},
        ]
    )

    # Test built-in dict access (should work as normal dict)
    assert collection["$0"]["patient"]["id"] == "123"
    assert collection["$1"]["patient"]["id"] == "456"
    assert collection["$2"]["patient"]["id"] == "789"

    # Test dict.get() method (inherited)
    assert collection.get("$0")["patient"]["name"] == "John"
    assert collection.get("$nonexistent") is None
    assert collection.get("$nonexistent", "default") == "default"

    # Test get_all method for extracting from all items
    all_ids = collection.get_all("patient.id")
    assert all_ids == ["123", "456", "789"]

    all_names = collection.get_all("patient.name")
    assert all_names == ["John", "Jane", "Bob"]

    all_statuses = collection.get_all("status")
    assert all_statuses == ["active", "inactive", "active"]

    # Test get_all with missing paths and defaults
    missing_field = collection.get_all("missing_field", default="N/A")
    assert missing_field == ["N/A", "N/A", "N/A"]

    # Test get_all with apply function
    upper_names = collection.get_all("patient.name", apply=str.upper)
    assert upper_names == ["JOHN", "JANE", "BOB"]


def test_filter_method():
    """Test the filter method."""
    collection = RecordSet(
        [
            {"name": "John", "age": 30, "active": True},
            {"name": "Jane", "age": 25, "active": False},
            {"name": "Bob", "age": 35, "active": True},
        ]
    )
    collection.append({"name": "Alice", "age": 28, "active": True}, key="alice")

    # Filter by active status
    active_collection = collection.filter(lambda x: x.get("active", False))
    assert len(active_collection) == 3

    # Check that numeric keys are reindexed
    assert "$0" in active_collection
    assert "$1" in active_collection
    assert "$2" in active_collection
    assert active_collection["$0"]["name"] == "John"
    assert active_collection["$1"]["name"] == "Bob"
    assert active_collection["$2"]["name"] == "Alice"

    # Check that custom key is preserved
    assert "$alice" in active_collection
    assert active_collection["$alice"]["name"] == "Alice"

    # Filter by age
    young_collection = collection.filter(lambda x: x.get("age", 0) < 30)
    assert len(young_collection) == 2
    assert list(young_collection)[0]["name"] == "Jane"
    assert list(young_collection)[1]["name"] == "Alice"


def test_map_method():
    """Test the map method."""
    collection = RecordSet([{"name": "John", "age": 30}, {"name": "Jane", "age": 25}])

    # Transform to add computed field
    enhanced = collection.map(lambda x: {**x, "adult": x.get("age", 0) >= 18})

    assert all("adult" in item for item in enhanced)
    assert all(item["adult"] is True for item in enhanced)


def test_to_json():
    """Test JSON serialization."""
    collection = RecordSet([{"id": 1, "name": "Test"}, {"id": 2, "name": "Another"}])

    # As dict
    json_str = collection.to_json()
    assert '"$0":' in json_str
    assert '"$1":' in json_str

    # As list
    json_list = collection.to_json(as_list=True)
    assert json_list.startswith("[")
    assert json_list.endswith("]")


def test_append_method():
    """Test appending items to collection."""
    collection = RecordSet()

    # Append with auto-generated key
    collection.append({"name": "John"})
    assert len(collection) == 1
    assert collection["$0"]["name"] == "John"

    # Append with specific key (should get $ prefix)
    collection.append({"name": "Jane"}, key="jane_key")
    assert collection["$jane_key"]["name"] == "Jane"
    assert len(collection) == 2

    # Append another auto-keyed item
    collection.append({"name": "Bob"})
    assert collection["$2"]["name"] == "Bob"
    assert len(collection) == 3

    # Test accessing named item with dict access
    assert collection["$jane_key"]["name"] == "Jane"


def test_complex_nested_access():
    """Test complex nested data access."""
    collection = RecordSet(
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

    # Access nested array element using get_all
    mrn = collection.get_all("patient.identifiers[0].value")
    assert mrn == ["MRN123"]

    # Access all encounter IDs using get_all
    encounter_ids = collection.get_all("encounters[*].id")
    assert encounter_ids == [["e1", "e2"]]

    # Access using dict access
    first_patient_id = collection["$0"]["patient"]["id"]
    assert first_patient_id == "123"

    # Test complex path with array using get_all
    all_identifiers = collection.get_all("patient.identifiers")
    assert len(all_identifiers[0]) == 2
    assert all_identifiers[0][0]["system"] == "MRN"
