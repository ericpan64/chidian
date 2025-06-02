"""Comprehensive tests for Piper mapping scenarios."""

from typing import Any

import chidian.partials as p
from chidian import DataMapping, Piper, get
from pydantic import BaseModel


# Test models for the new API
class SourceData(BaseModel):
    data: dict = {}


class ProcessedData(BaseModel):
    patient_id: str
    is_active: bool
    status: str


class TestPiper:
    """Test Piper functionality with DataMapping."""

    def test_simple_mapping(self, simple_data: dict[str, Any]) -> None:
        """Test basic Piper functionality with callable mapping."""

        def mapping(data: dict) -> dict:
            return {
                "patient_id": get(data, "data.patient.id"),
                "is_active": get(data, "data.patient.active"),
                "status": "processed",
            }

        data_mapping = DataMapping(SourceData, ProcessedData, mapping)
        piper: Piper = Piper(data_mapping)
        result = piper(SourceData.model_validate(simple_data))

        assert isinstance(result, ProcessedData)
        assert result.patient_id == "abc123"
        assert result.is_active
        assert result.status == "processed"

    def test_callable_mapping_with_partials(self) -> None:
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
            "address": "123 Main St|Boston|02101",
        }

        def mapper(data: dict) -> dict:
            # Use new partials API
            name_template = p.template("{} {}")
            status_classifier = p.get("status") >> p.case(
                {"active": "✓ Active", "inactive": "✗ Inactive"}, default="Unknown"
            )
            city_extractor = p.get("address") >> p.split("|") >> p.at_index(1)

            return {
                "name": name_template(get(data, "firstName"), get(data, "lastName")),
                "status_display": status_classifier(data),
                "all_codes": p.flatten(["codes"], delimiter=", ")(data),
                "city": city_extractor(data),
                "backup_name": p.coalesce("nickname", "firstName", default="Guest")(
                    data
                ),
            }

        data_mapping = DataMapping(PersonSource, PersonTarget, mapper)
        piper: Piper = Piper(data_mapping)
        result = piper(PersonSource.model_validate(data))

        assert isinstance(result, PersonTarget)
        assert result.name == "John Doe"
        assert result.status_display == "✓ Active"
        assert result.all_codes == "A, B, C"
        assert result.city == "Boston"
        assert result.backup_name == "John"
