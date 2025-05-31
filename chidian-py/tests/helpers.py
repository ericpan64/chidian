"""Helper functions and mappers for tests."""

from typing import Any, Callable
from chidian import get
from chidian.seeds import MERGE, CASE, COALESCE, SPLIT
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
    return {
        "id": get(data, "id"),
        "patient_id": SPLIT("subject.reference", "/", -1).process(data),
        "code": get(data, "code.coding[0].code"),
        "value": get(data, "valueQuantity.value"),
        "unit": get(data, "valueQuantity.unit", default="")
    }


def name_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map complex name structures."""
    return {
        "full_name": MERGE("name.given[0]", "name.family", template="{} {}").process(data),
        "display": COALESCE(["name.text", "name.family"], default="Unknown").process(data)
    }


def address_mapper(data: dict[str, Any]) -> dict[str, Any]:
    """Map address with type classification."""
    return {
        "type": CASE("use", {"home": "🏠", "work": "🏢", "old": "📍"}, default="📮").process(data),
        "full": MERGE("line[0]", "city", "postalCode", template="{}, {} {}").process(data)
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