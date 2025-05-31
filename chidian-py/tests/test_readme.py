"""Tests based on examples from the README file.

These tests serve as documentation examples showing common usage patterns.
"""

import pytest
from chidian import get, DictPiper
from chidian.seeds import MERGE, FLATTEN, COALESCE, SPLIT, DROP, KEEP, CASE

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
    
    # Create mapper function using new SEED processing approach
    def mapper(data):
        return {
            "full_name": MERGE("name[0].given[0]", "name[0].family", template="{} {}").process(data),
            "date_of_birth": get(data, "birthDate"),
            "administrative_gender": CASE("gender", {
                "male": "Male",
                "female": "Female",
                "other": "Other"
            }, default="Unknown").process(data),
            "old_address": MERGE(
                "address[-1].line[0]",
                "address[-1].city",
                "address[-1].postalCode",
                template="{}\n{}, {}"
            ).process(data),
            "all_ids": FLATTEN(["id"], delimiter=", ").process(data),
            "mrn": COALESCE(["id"], default="unknown").process(data),
            "address_type": CASE("address[-1].use", {
                "home": "🏠 Home Address",
                "work": "🏢 Work Address", 
                "old": "📍 Previous Address"
            }, default="📮 Other Address").process(data)
        }
    
    # Execute transformation
    piper = DictPiper(mapper)
    result = piper.run(data_a)
    
    # Verify expected output
    assert result["full_name"] == "Pieter van de Heuvel"
    assert result["date_of_birth"] == "1944-11-17"
    assert result["administrative_gender"] == "Male"  # Transformed via CASE
    assert result["old_address"] == "Oudergracht 7\nUtrecht, 3511 AE"
    assert result["all_ids"] == "f001"
    assert result["mrn"] == "f001"
    assert result["address_type"] == "📍 Previous Address"


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
    
    # Create reverse mapper function using new SEED API
    def mapper(data):
        address_parts = get(data, "old_address").split("\n") if get(data, "old_address") else []
        city_postal = address_parts[1].split(", ") if len(address_parts) > 1 else ["", ""]
        
        return {
            "resourceType": "Patient",
            "id": get(data, "mrn"),
            "name": [{
                "use": "official",
                "given": [SPLIT("full_name", " ", 0).process(data)],
                "family": SPLIT("full_name", " ", 1, then=lambda x: " ".join(get(data, "full_name").split(" ")[1:]) if x else "").process(data)
            }],
            "gender": CASE("administrative_gender", {
                "Male": "male",
                "Female": "female", 
                "Other": "other",
                "male": "male",  # Handle the case where it's already lowercase
                "female": "female",
                "other": "other"
            }, default="unknown").process(data),
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
    assert result["gender"] == "male"  # Reverse transformed via CASE
    assert result["birthDate"] == "1944-11-17"
    assert result["address"][0]["line"][0] == "Van Egmondkade 23"
    assert result["address"][0]["city"] == "Amsterdam"
    assert result["address"][0]["postalCode"] == "1024 RJ"


def test_merge_seed():
    """Test MERGE seed functionality from README using new API."""
    data = {
        "firstName": "John",
        "lastName": "Doe",
        "middleName": "James"
    }
    
    # Test basic merge
    merge_fn = MERGE("firstName", "lastName", template="{} {}")
    assert merge_fn.process(data) == "John Doe"
    
    # Test merge with missing values
    merge_fn_skip = MERGE("firstName", "missing", "lastName", template="{} {} {}", skip_none=True)
    assert merge_fn_skip.process(data) == "John Doe"
    
    # Test merge with all values
    merge_fn_all = MERGE("firstName", "middleName", "lastName", template="{} {} {}")
    assert merge_fn_all.process(data) == "John James Doe"


def test_flatten_seed():
    """Test FLATTEN seed functionality from README using new API."""
    data = {
        "ids": ["123", "456", "789"],
        "codes": ["A", "B", "C"]
    }
    
    # Test basic flatten
    flatten_fn = FLATTEN(["ids"], delimiter=", ")
    assert flatten_fn.process(data) == "123, 456, 789"
    
    # Test flatten multiple sources
    flatten_multi = FLATTEN(["ids", "codes"], delimiter=" | ")
    assert flatten_multi.process(data) == "123 | 456 | 789 | A | B | C"


def test_coalesce_seed():
    """Test COALESCE seed functionality from README using new API."""
    data = {
        "primary": None,
        "secondary": "",
        "tertiary": "value3"
    }
    
    # Test coalesce with first non-empty value
    coalesce_fn = COALESCE(["primary", "secondary", "tertiary"], default="none")
    assert coalesce_fn.process(data) == "value3"
    
    # Test coalesce with all empty, use default
    empty_data = {"primary": None, "secondary": None}
    assert coalesce_fn.process(empty_data) == "none"


def test_split_seed():
    """Test SPLIT seed functionality from README using new API."""
    data = {
        "full_name": "John James Doe",
        "address": "123 Main St\nNew York, NY 10001"
    }
    
    # Test split first name
    split_first = SPLIT("full_name", " ", 0)
    assert split_first.process(data) == "John"
    
    # Test split last name
    split_last = SPLIT("full_name", " ", -1)
    assert split_last.process(data) == "Doe"
    
    # Test split with transformation
    split_city = SPLIT("address", "\n", 1, then=lambda x: x.split(", ")[0] if x else None)
    assert split_city.process(data) == "New York"


def test_complex_nested_transformation():
    """Test complex nested transformation with multiple seeds using new API."""
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
        return {
            "primary_name": MERGE(
                "patient.names[0].given[0]", 
                "patient.names[0].family", 
                template="{} {}"
            ).process(data),
            "nickname": COALESCE([
                "patient.names[1].given[0]",
                "patient.names[0].given[1]"
            ], default="").process(data),
            "contact_display": CASE("patient.telecom[0].system", {
                "phone": "📞 " + get(data, "patient.telecom[0].value", ""),
                "email": "📧 " + get(data, "patient.telecom[0].value", ""),
                "fax": "📠 " + get(data, "patient.telecom[0].value", "")
            }, default="📮 " + get(data, "patient.telecom[0].value", "")).process(data),
            "all_contacts": FLATTEN([
                "patient.telecom[*].value"
            ], delimiter=" | ").process(data),
            "name_count": len(get(data, "patient.names", [])),
            "has_nickname": CASE("patient.names[1].use", {
                "nickname": True,
                lambda x: x is not None: False
            }, default=False).process(data)
        }
    
    piper = DictPiper(mapper)
    result = piper(data)
    
    assert result["primary_name"] == "John Doe"
    assert result["nickname"] == "Johnny"
    assert result["contact_display"] == "📞 555-1234"
    assert result["all_contacts"] == "555-1234 | john@example.com"
    assert result["name_count"] == 2
    assert result["has_nickname"] == True


def test_error_handling():
    """Test error handling in transformations using new API."""
    data = {"name": "John"}
    
    # Test with invalid path
    assert get(data, "invalid.path.here") is None
    
    # Test with invalid index
    assert get(data, "name[10]") is None
    
    # Test MERGE with all missing values
    merge_fn = MERGE("missing1", "missing2", template="{} {}")
    assert merge_fn.process(data) == "None None"  # Template with None values
    
    # Test SPLIT with missing data
    split_fn = SPLIT("missing", " ", 0)
    assert split_fn.process(data) is None
    
    # Test COALESCE fallback behavior
    coalesce_fn = COALESCE(["missing1", "missing2"], default="fallback")
    assert coalesce_fn.process(data) == "fallback"
    
    # Test CASE with missing data
    case_fn = CASE("missing.field", {"value": "result"}, default="no_match")
    assert case_fn.process(data) == "no_match"