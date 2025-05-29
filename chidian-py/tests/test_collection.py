import pytest
from chidian.collection import DataCollection

def test_basic_collection():
    """Test basic DataCollection functionality."""
    # Create from list
    items = [
        {"id": "p1", "name": "John", "age": 30},
        {"id": "p2", "name": "Jane", "age": 25},
        {"id": "p3", "name": "Bob", "age": 35}
    ]
    
    collection = DataCollection(items)
    
    # Test length
    assert len(collection) == 3
    
    # Test iteration
    assert list(collection) == items
    
    # Test dict-like access
    assert collection["0"]["name"] == "John"
    assert collection["1"]["name"] == "Jane"

def test_get_method():
    """Test the get method with various paths."""
    collection = DataCollection([
        {"patient": {"id": "123", "name": "John"}, "status": "active"},
        {"patient": {"id": "456", "name": "Jane"}, "status": "inactive"},
        {"patient": {"id": "789", "name": "Bob"}, "status": "active"}
    ])
    
    # Direct access
    assert collection.get("0")["patient"]["id"] == "123"
    
    # Path access
    assert collection.get("0.patient.name") == "John"
    
    # $0 syntax to access items list
    assert len(collection.get("$0")) == 3
    assert collection.get("$0[0].patient.name") == "John"
    assert collection.get("$0[1].patient.id") == "456"
    assert collection.get("$0[:2]")[0]["patient"]["name"] == "John"
    
    # With apply function on single item
    upper_name = collection.get("0.patient.name", apply=str.upper)
    assert upper_name == "JOHN"

def test_select_method():
    """Test the select method."""
    collection = DataCollection([
        {"type": "patient", "data": {"id": "p1", "status": "active"}},
        {"type": "patient", "data": {"id": "p2", "status": "inactive"}},
        {"type": "encounter", "data": {"id": "e1", "patient": "p1"}},
        {"type": "patient", "data": {"id": "p3", "status": "active"}}
    ])
    
    # Select all items
    all_items = collection.select()
    assert len(all_items) == 4
    
    # Select data field from all items
    all_data = collection.select("data")
    assert len(all_data) == 4
    assert all("id" in item for item in all_data)
    
    # Select with filter
    patients_only = collection.select(where=lambda x: x.get("type") == "patient")
    assert len(patients_only) == 3
    
    # Select data field with filter
    active_data = collection.select("data", where=lambda x: x.get("data", {}).get("status") == "active")
    assert len(active_data) == 2
    assert all(item.get("status") == "active" for item in active_data)

def test_filter_method():
    """Test the filter method."""
    collection = DataCollection([
        {"name": "John", "age": 30, "active": True},
        {"name": "Jane", "age": 25, "active": False},
        {"name": "Bob", "age": 35, "active": True}
    ])
    
    # Filter by active status
    active_collection = collection.filter(lambda x: x.get("active", False))
    assert len(active_collection) == 2
    
    # Filter by age
    young_collection = collection.filter(lambda x: x.get("age", 0) < 30)
    assert len(young_collection) == 1
    assert list(young_collection)[0]["name"] == "Jane"

def test_map_method():
    """Test the map method."""
    collection = DataCollection([
        {"name": "John", "age": 30},
        {"name": "Jane", "age": 25}
    ])
    
    # Transform to add computed field
    enhanced = collection.map(lambda x: {**x, "adult": x.get("age", 0) >= 18})
    
    assert all("adult" in item for item in enhanced)
    assert all(item["adult"] is True for item in enhanced)

def test_to_json():
    """Test JSON serialization."""
    collection = DataCollection([
        {"id": 1, "name": "Test"},
        {"id": 2, "name": "Another"}
    ])
    
    # As dict
    json_str = collection.to_json()
    assert '"0":' in json_str
    assert '"1":' in json_str
    
    # As list
    json_list = collection.to_json(as_list=True)
    assert json_list.startswith('[')
    assert json_list.endswith(']')

def test_add_method():
    """Test adding items to collection."""
    collection = DataCollection()
    
    # Add with auto-generated key
    collection.add({"name": "John"})
    assert len(collection) == 1
    assert collection["0"]["name"] == "John"
    
    # Add with specific key
    collection.add({"name": "Jane"}, key="jane_key")
    assert collection["jane_key"]["name"] == "Jane"
    assert len(collection) == 2

def test_complex_nested_access():
    """Test complex nested data access."""
    collection = DataCollection([
        {
            "patient": {
                "id": "123",
                "identifiers": [
                    {"system": "MRN", "value": "MRN123"},
                    {"system": "SSN", "value": "SSN456"}
                ]
            },
            "encounters": [
                {"id": "e1", "date": "2024-01-01"},
                {"id": "e2", "date": "2024-02-01"}
            ]
        }
    ])
    
    # Access nested array element
    mrn = collection.get("0.patient.identifiers[0].value")
    assert mrn == "MRN123"
    
    # Access all encounter IDs using direct path
    encounter_ids = collection.get("0.encounters[*].id")
    assert encounter_ids == ["e1", "e2"]
    
    # Access using $0 syntax
    first_patient_id = collection.get("$0[0].patient.id")
    assert first_patient_id == "123"
