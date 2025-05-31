"""Comprehensive tests for Piper mapping scenarios."""

from typing import Any
import pytest

from chidian import get, Piper, template, case, first_non_empty, flatten
import chidian.partials as p
from chidian.seeds import DROP, KEEP
from tests.helpers import (
    patient_mapper, observation_mapper, name_mapper, address_mapper,
    assert_patient, assert_observation, assert_name, assert_address,
    create_loinc_mapper
)


class TestPiper:
    """Test Piper functionality for dict-to-dict transformations."""
    
    @pytest.mark.parametrize("mapper,input_data,assert_fn", [
        (patient_mapper, {"patient": {"id": "123", "name": "John", "active": True}}, assert_patient),
        (observation_mapper, {
            "id": "obs-1",
            "subject": {"reference": "Patient/456"},
            "code": {"coding": [{"code": "8480-6"}]},
            "valueQuantity": {"value": 140, "unit": "mmHg"}
        }, assert_observation),
        (name_mapper, {"name": {"given": ["John"], "family": "Doe"}}, assert_name),
        (address_mapper, {
            "use": "home",
            "line": ["123 Main St"],
            "city": "Boston",
            "postalCode": "02101"
        }, assert_address),
    ])
    def test_mapper_variants(self, mapper, input_data, assert_fn):
        """Test various mapper functions with parameterized inputs."""
        piper = Piper(mapper, source_type=dict, target_type=dict)
        result = piper(input_data)
        assert_fn(result)
        
    def test_simple_mapping(self, simple_data: dict[str, Any]):
        """Test basic Piper functionality for dict transformations."""
        def mapping(data: dict[str, Any]) -> dict[str, Any]:
            return {
                "patient_id": get(data, "data.patient.id"),
                "is_active": get(data, "data.patient.active"),
                "status": "processed"
            }
        
        piper = Piper(mapping, source_type=dict, target_type=dict)
        result = piper(simple_data)
        
        assert result == {
            "patient_id": "abc123",
            "is_active": True,
            "status": "processed"
        }
        
    def test_seed_operations(self):
        """Test Piper with various SEED operations."""
        data = {
            "firstName": "John",
            "lastName": "Doe", 
            "status": "active",
            "codes": ["A", "B", "C"],
            "address": "123 Main St|Boston|02101"
        }
        
        def mapper(data: dict[str, Any]) -> dict[str, Any]:
            # Use new partials API
            name_template = template("{} {}")
            status_classifier = p.get("status") >> case({
                "active": "✓ Active",
                "inactive": "✗ Inactive"
            }, default="Unknown")
            city_extractor = p.get("address") >> p.split("|") >> p.at_index(1)
            
            return {
                "name": name_template(get(data, "firstName"), get(data, "lastName")),
                "status_display": status_classifier(data),
                "all_codes": flatten(["codes"], delimiter=", ")(data),
                "city": city_extractor(data),
                "backup_name": first_non_empty("nickname", "firstName", default="Guest")(data)
            }
            
        piper = Piper(mapper, source_type=dict, target_type=dict)
        result = piper(data)
        
        assert result["name"] == "John Doe"
        assert result["status_display"] == "✓ Active"
        assert result["all_codes"] == "A, B, C"
        assert result["city"] == "Boston"
        assert result["backup_name"] == "John"


class TestPiperConditional:
    """Test conditional logic in Piper."""
    
    def test_drop_conditions(self):
        """Test DROP seed with conditions."""
        data_list = [
            {"id": 1, "active": True, "value": 100},
            {"id": 2, "active": False, "value": 0},
            {"id": 3, "active": True, "value": 50}
        ]
        
        def mapper(item: dict[str, Any]) -> dict[str, Any]:
            # Drop inactive items
            if not item.get("active"):
                return DROP.this_object()
            
            # Drop items with low values
            if item.get("value", 0) < 75:
                return DROP.this_object()
                
            return {"id": item["id"], "value": item["value"]}
        
        results = [Piper(mapper, source_type=dict, target_type=dict)(item) for item in data_list]
        # Filter out DROP results
        results = [r for r in results if not isinstance(r, DROP)]
        
        assert len(results) == 1
        assert results[0] == {"id": 1, "value": 100}
        
    def test_keep_conditions(self):
        """Test KEEP seed preserving values."""
        data = {"type": "important", "value": "preserve_me"}
        
        def mapper(data: dict[str, Any]) -> dict[str, Any]:
            if data.get("type") == "important":
                return {"value": KEEP(data["value"]).value}
            return {"value": "default"}
            
        piper = Piper(mapper, source_type=dict, target_type=dict)
        result = piper(data)
        
        assert result["value"] == "preserve_me"


class TestPiperIntegration:
    """Test Piper with complex integrations."""
    
    def test_nested_transformation(self, fhir_bundle):
        """Test transforming nested FHIR bundle."""
        code_mapper = create_loinc_mapper()
        
        def observation_transform(obs: dict[str, Any]) -> dict[str, Any]:
            code = get(obs, "code.coding[0].code")
            return {
                "id": get(obs, "id"),
                "type": code_mapper.get(code, "unknown"),
                "patient": (p.get("subject.reference") >> p.split("/") >> p.last)(obs),
                "components": [
                    {
                        "code": code_mapper.get(get(comp, "code.coding[0].code"), "unknown"),
                        "value": get(comp, "valueQuantity.value")
                    }
                    for comp in get(obs, "component", [])
                ]
            }
        
        # Transform all observations
        observations = get(fhir_bundle, "entry[*].resource")
        results = [Piper(observation_transform, source_type=dict, target_type=dict)(obs) for obs in observations]
        
        assert len(results) == 2
        assert results[0]["type"] == "blood_pressure"
        assert results[0]["patient"] == "123"
        assert results[0]["components"][0]["code"] == "systolic_bp"
        assert results[1]["patient"] == "456"