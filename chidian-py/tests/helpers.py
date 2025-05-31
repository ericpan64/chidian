"""Helper functions and mappers for tests."""

from typing import Any, Callable
from chidian import get
from chidian import template, case, first_non_empty
import chidian.partials as p
from chidian.lexicon import Lexicon


# Common mappers used across tests
def patient_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Simple patient data mapper."""
    return {
        "id": get(data, "patient.id"),
        "name": get(data, "patient.name"),
        "active": get(data, "patient.active")
    }


def observation_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map FHIR observation to flat structure."""
    # Use partials for cleaner extraction
    extract_patient_id = p.get("subject.reference") >> p.split("/") >> p.last
    
    return {
        "id": get(data, "id"),
        "patient_id": extract_patient_id(data),
        "code": get(data, "code.coding[0].code"),
        "value": get(data, "valueQuantity.value"),
        "unit": get(data, "valueQuantity.unit", default="")
    }


def name_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map complex name structures."""
    name_template = template("{} {}")
    
    return {
        "full_name": name_template(
            get(data, "name.given[0]"),
            get(data, "name.family")
        ),
        "display": first_non_empty("name.text", "name.family", default="Unknown")(data)
    }


def address_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map address with type classification."""
    type_classifier = p.get("use") >> case({"home": "🏠", "work": "🏢", "old": "📍"}, default="📮")
    address_template = template("{}, {} {}")
    
    return {
        "type": type_classifier(data),
        "full": address_template(
            get(data, "line[0]"),
            get(data, "city"),
            get(data, "postalCode")
        )
    }


# Assertion helpers for parameterized tests
def assert_patient(result: dict[str, Any]) -> None:
    """Assert basic patient structure."""
    assert "id" in result
    assert "name" in result
    assert isinstance(result.get("active"), bool)


def assert_observation(result: dict[str, Any]) -> None:
    """Assert observation structure."""
    assert "id" in result
    assert "patient_id" in result
    assert "code" in result
    assert "value" in result or "unit" in result


def assert_name(result: dict[str, Any]) -> None:
    """Assert name structure."""
    assert "full_name" in result or "display" in result
    assert not (result.get("full_name", "").startswith("None"))


def assert_address(result: dict[str, Any]) -> None:
    """Assert address structure."""
    assert "type" in result
    assert result["type"] in ["🏠", "🏢", "📍", "📮"]
    assert "full" in result


# Standard code mappers
def create_loinc_mapper() -> Lexicon:
    """Create standard LOINC to readable name mappings."""
    return Lexicon({
        "8480-6": "systolic_bp",
        "8462-4": "diastolic_bp",
        "85354-9": "blood_pressure",
        "2160-0": "creatinine",
        "33747-0": "general_status"
    })


def create_gender_mapper() -> Lexicon:
    """Create gender code mappings."""
    return Lexicon({
        "male": "M",
        "female": "F",
        "other": "O",
        "unknown": "U"
    })