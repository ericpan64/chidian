"""Tests based on examples from the README file.

NOTE: These tests are currently expected to fail as the core functions
(get, put, DictPiper, and seeds) are not yet implemented - they're 
placeholders with `...` in the source code.
"""

import pytest
from chidian import get, DictPiper
from chidian.seeds import MERGE, FLATTEN, COALESCE, SPLIT, DROP, KEEP

def test_get_function_basic():
    """Test basic get function as shown in README."""
    data = {
        "patient": {
            "name": {
                "given": ["John", "James"],
                "family": "Doe"
            },
            "id": "12345"
        }
    }
    
    # Test basic path navigation
    assert get(data, "patient.id") == "12345"
    assert get(data, "patient.name.family") == "Doe"
    assert get(data, "patient.name.given[0]") == "John"
    assert get(data, "patient.name.given[1]") == "James"
    
    # Test missing paths
    assert get(data, "patient.missing") is None
    assert get(data, "patient.name.middle") is None


def test_readme_a_to_b_transformation():
    """Test the A->B transformation from README example."""
    # Input data (A.json structure)
    data_a = {
        "resourceType": "Patient",
        "id": "f001",
        "name": [{
            "use": "official",
            "family": "van de Heuvel",
            "given": ["Pieter"],
            "suffix": ["MSc"]
        }],
        "gender": "male",
        "birthDate": "1944-11-17",
        "address": [
            {
                "use": "home",
                "line": ["Van Egmondkade 23"],
                "city": "Amsterdam",
                "postalCode": "1024 RJ",
                "country": "NLD"
            },
            {
                "use": "old",
                "line": ["Oudergracht 7"],
                "city": "Utrecht",
                "postalCode": "3511 AE",
                "country": "NLD"
            }
        ]
    }
    
    # Create mapper function following README pattern
    def mapper(data):
        return {
            "full_name": MERGE(get, "name[0].given[0]", "name[0].family", template="{} {}")(data),
            "date_of_birth": get(data, "birthDate"),
            "administrative_gender": get(data, "gender"),
            "old_address": MERGE(
                get,
                "address[-1].line[0]",
                "address[-1].city",
                "address[-1].postalCode",
                template="{}\n{}, {}"
            )(data),
            "all_ids": FLATTEN(get, ["id"], delimiter=", ")(data),
            "mrn": COALESCE(get, ["id"], default="unknown")(data)  # Simplified - no MR identifier in test data
        }
    
    # Execute transformation
    piper = DictPiper(mapper)
    result = piper.run(data_a)
    
    # Verify expected output
    assert result["full_name"] == "Pieter van de Heuvel"
    assert result["date_of_birth"] == "1944-11-17"
    assert result["administrative_gender"] == "male"
    assert result["old_address"] == "Oudergracht 7\nUtrecht, 3511 AE"
    assert result["all_ids"] == "f001"
    assert result["mrn"] == "f001"  # Falls back to id since no MR identifier


def test_readme_b_to_a_transformation():
    """Test the B->A reverse transformation from README example."""
    # Input data (B.json structure)
    data_b = {
        "full_name": "Pieter van de Heuvel",
        "date_of_birth": "1944-11-17",
        "administrative_gender": "male",
        "old_address": "Van Egmondkade 23\nAmsterdam, 1024 RJ",
        "all_ids": "f001",
        "mrn": "f001"
    }
    
    # Create reverse mapper function
    def mapper(data):
        address_parts = data.get("old_address", "").split("\n")
        city_postal = address_parts[1].split(", ") if len(address_parts) > 1 else ["", ""]
        
        return {
            "resourceType": "Patient",
            "id": get(data, "mrn"),
            "name": [{
                "use": "official",
                "given": [SPLIT(get, "full_name", pattern=" ", part=0)(data)],
                "family": " ".join(get(data, "full_name").split(" ")[1:]) if get(data, "full_name") else ""
            }],
            "gender": get(data, "administrative_gender"),
            "birthDate": get(data, "date_of_birth"),
            "address": [{
                "use": "old",
                "line": [address_parts[0] if address_parts else ""],
                "city": city_postal[0] if len(city_postal) > 0 else "",
                "postalCode": city_postal[1] if len(city_postal) > 1 else ""
            }]
        }
    
    # Execute transformation
    piper = DictPiper(mapper)
    result = piper.run(data_b)
    
    # Verify structure
    assert result["resourceType"] == "Patient"
    assert result["id"] == "f001"
    assert result["name"][0]["given"][0] == "Pieter"
    assert result["name"][0]["family"] == "van de Heuvel"
    assert result["gender"] == "male"
    assert result["birthDate"] == "1944-11-17"
    assert result["address"][0]["line"][0] == "Van Egmondkade 23"
    assert result["address"][0]["city"] == "Amsterdam"
    assert result["address"][0]["postalCode"] == "1024 RJ"


def test_merge_seed():
    """Test MERGE seed functionality from README."""
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "middleName": "James"
    }
    
    # Test basic merge
    merge_fn = MERGE(get, "firstName", "lastName", template="{} {}")
    assert merge_fn(data) == "John Doe"
    
    # Test merge with missing values
    merge_fn_skip = MERGE(get, "firstName", "missing", "lastName", template="{} {} {}", skip_none=True)
    assert merge_fn_skip(data) == "John Doe"
    
    # Test merge with all values
    merge_fn_all = MERGE(get, "firstName", "middleName", "lastName", template="{} {} {}")
    assert merge_fn_all(data) == "John James Doe"


def test_flatten_seed():
    """Test FLATTEN seed functionality from README."""
    data = {
        "ids": ["123", "456", "789"],
        "codes": ["A", "B", "C"]
    }
    
    # Test basic flatten
    flatten_fn = FLATTEN(get, ["ids"], delimiter=", ")
    assert flatten_fn(data) == "123, 456, 789"
    
    # Test flatten multiple sources
    flatten_multi = FLATTEN(get, ["ids", "codes"], delimiter=" | ")
    assert flatten_multi(data) == "123 | 456 | 789 | A | B | C"


def test_coalesce_seed():
    """Test COALESCE seed functionality from README."""
    data = {
        "primary": None,
        "secondary": "",
        "tertiary": "value3"
    }
    
    # Test coalesce with first non-empty value
    coalesce_fn = COALESCE(get, ["primary", "secondary", "tertiary"], default="none")
    assert coalesce_fn(data) == "value3"
    
    # Test coalesce with all empty, use default
    empty_data = {"primary": None, "secondary": None}
    assert coalesce_fn(empty_data) == "none"


def test_split_seed():
    """Test SPLIT seed functionality from README."""
    data = {
        "full_name": "John James Doe",
        "address": "123 Main St\nNew York, NY 10001"
    }
    
    # Test split first name
    split_first = SPLIT(get, "full_name", pattern=" ", part=0)
    assert split_first(data) == "John"
    
    # Test split last name
    split_last = SPLIT(get, "full_name", pattern=" ", part=-1)
    assert split_last(data) == "Doe"
    
    # Test split with transformation
    split_city = SPLIT(get, "address", pattern="\n", part=1, then=lambda x: x.split(", ")[0] if x else None)
    assert split_city(data) == "New York"


def test_complex_nested_transformation():
    """Test complex nested transformation with multiple seeds."""
    data = {
        "patient": {
            "names": [
                {"given": ["John", "J."], "family": "Doe"},
                {"given": ["Johnny"], "family": "Doe", "use": "nickname"}
            ],
            "telecom": [
                {"system": "phone", "value": "555-1234"},
                {"system": "email", "value": "john@example.com"}
            ]
        }
    }
    
    def mapper(data):
        # Find first non-nickname name
        names = data.get("patient", {}).get("names", [])
        primary_name = next((n for n in names if n.get("use") != "nickname"), None)
        nickname_name = next((n for n in names if n.get("use") == "nickname"), None)
        
        return {
            "primary_name": (primary_name.get("given", [""])[0] + " " + primary_name.get("family", "")) if primary_name else "",
            "nickname": nickname_name.get("given", [""])[0] if nickname_name else "",
            "contact_info": " | ".join([tc.get("value", "") for tc in data.get("patient", {}).get("telecom", [])])
        }
    
    piper = DictPiper(mapper)
    result = piper.run(data)
    
    assert result["primary_name"] == "John Doe"
    assert result["nickname"] == "Johnny"
    assert result["contact_info"] == "555-1234 | john@example.com"


def test_error_handling():
    """Test error handling in transformations."""
    data = {"name": "John"}
    
    # Test with invalid path
    assert get(data, "invalid.path.here") is None
    
    # Test with invalid index
    assert get(data, "name[10]") is None
    
    # Test MERGE with all missing values
    merge_fn = MERGE(get, "missing1", "missing2", template="{} {}")
    assert merge_fn(data) == "None None"  # Template with None values
    
    # Test SPLIT with missing data
    split_fn = SPLIT(get, "missing", pattern=" ", part=0)
    assert split_fn(data) is None