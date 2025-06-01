"""Comprehensive tests for Piper mapping scenarios."""

from typing import Any, Optional
import pytest
from pydantic import BaseModel

from chidian import get, Piper, DataMapping, template, case, first_non_empty, flatten
import chidian.partials as p
from chidian.seeds import DROP, KEEP


# Test models for the new API
class SourceData(BaseModel):
    data: dict = {}
    
class ProcessedData(BaseModel):
    patient_id: str
    is_active: bool
    status: str


class TestPiper:
    """Test Piper functionality with DataMapping."""
        
    def test_simple_mapping(self, simple_data: dict[str, Any]):
        """Test basic Piper functionality with callable mapping."""
        def mapping(data: dict) -> dict:
            return {
                "patient_id": get(data, "data.patient.id"),
                "is_active": get(data, "data.patient.active"),
                "status": "processed"
            }
        
        data_mapping = DataMapping(SourceData, ProcessedData, mapping)
        piper = Piper(data_mapping)
        result = piper(SourceData.model_validate(simple_data))
        
        assert isinstance(result, ProcessedData)
        assert result.patient_id == "abc123"
        assert result.is_active == True
        assert result.status == "processed"
        
    def test_callable_mapping_with_partials(self):
        """Test DataMapping with callable mapping using partials API."""
        
        class PersonSource(BaseModel):
            firstName: str
            lastName: str
            status: str
            codes: list[str]
            address: str
            
        class PersonTarget(BaseModel):
            name: str
            status_display: str
            all_codes: str
            city: str
            backup_name: str
        
        data = {
            "firstName": "John",
            "lastName": "Doe", 
            "status": "active",
            "codes": ["A", "B", "C"],
            "address": "123 Main St|Boston|02101"
        }
        
        def mapper(data: dict) -> dict:
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
            
        data_mapping = DataMapping(PersonSource, PersonTarget, mapper)
        piper = Piper(data_mapping)
        result = piper(PersonSource.model_validate(data))
        
        assert isinstance(result, PersonTarget)
        assert result.name == "John Doe"
        assert result.status_display == "✓ Active"
        assert result.all_codes == "A, B, C"
        assert result.city == "Boston"
        assert result.backup_name == "John"


# Commenting out SEED-based tests since SEED processing is now handled within 
# DataMapping callable mappings rather than by Piper
# class TestPiperConditional:
#     """Test conditional logic in Piper."""

# TODO: Update remaining tests to use new DataMapping API
# The following tests need to be updated to use DataMapping with callable mappings
# instead of the old dict-to-dict Piper mode:
# - SEED operations (DROP, KEEP) should be handled within the mapping function
# - Complex transformations should use DataMapping with Pydantic models
# - Integration tests should be refactored to use the new API