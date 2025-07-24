"""Comprehensive tests for special types (DROP, KEEP) with Mapper and DataMapping."""

from typing import Any

from chidian import DROP, KEEP, DataMapping, Mapper, get
from tests.structstest import (
    ComplexPersonData,
    FlatPersonData,
    KeepTestTarget,
    SimpleTarget,
    SourceData,
)


class TestSeedProcessing:
    """Test special type value processing independently."""

    def test_drop_enum_values(self) -> None:
        """Test DROP enum values and level property."""
        assert DROP.THIS_OBJECT.value == -1
        assert DROP.PARENT.value == -2
        assert DROP.GRANDPARENT.value == -3
        assert DROP.GREATGRANDPARENT.value == -4

        assert DROP.THIS_OBJECT.level == -1
        assert DROP.PARENT.level == -2

    def test_drop_process_method(self) -> None:
        """Test DROP process method returns itself."""
        result = DROP.THIS_OBJECT.process({"test": "data"})
        # The Python implementation returns the DROP enum itself
        assert result == DROP.THIS_OBJECT
        assert result.level == DROP.THIS_OBJECT.value

    def test_keep_value_preservation(self) -> None:
        """Test KEEP preserves values correctly."""
        # Test basic value preservation
        assert KEEP({}).value == {}
        assert KEEP([]).value == []
        assert KEEP("").value == ""
        assert KEEP(None).value is None

        # Test process method returns the wrapped value
        keep_obj = KEEP("test_value")
        assert keep_obj.process({"irrelevant": "data"}) == "test_value"

    def test_keep_complex_values(self) -> None:
        """Test KEEP with complex data structures."""
        complex_data = {"nested": {"list": [1, 2, 3]}, "simple": "value"}
        keep_obj = KEEP(complex_data)

        assert keep_obj.value == complex_data
        assert keep_obj.process({}) == complex_data


class TestSeedsWithDataMapping:
    """Test special type integration with DataMapping and Mapper."""

    def test_simple_data_flow_without_special_types(
        self, simple_data: dict[str, Any]
    ) -> None:
        """Test baseline data flow without any special type objects."""
        from chidian.partials import get as p_get

        mapping = {
            "patient_id": p_get("data.patient.id"),
            "is_active": p_get("data.patient.active"),
        }

        data_mapping = DataMapping(
            transformations=mapping, input_schema=SourceData, output_schema=SimpleTarget
        )
        mapper = Mapper(data_mapping)
        result = mapper(SourceData.model_validate(simple_data))

        assert isinstance(result, SimpleTarget)
        assert result.patient_id == "abc123"
        assert result.is_active is True

    def test_keep_in_transformation(self) -> None:
        """Test KEEP objects in data transformations.

        Note: This test demonstrates that special type processing is not yet implemented
        in the current DataMapping/Mapper system. KEEP objects need to be processed
        to extract their values before Pydantic validation.
        """
        # For now, manually process KEEP objects since automatic processing isn't implemented
        keep_obj = KEEP("processed_string")

        mapping = {
            "processed_value": lambda _data: keep_obj.process({}),
            "regular_value": lambda _data: "regular_string",
        }

        data_mapping = DataMapping(
            transformations=mapping,
            input_schema=SourceData,
            output_schema=KeepTestTarget,
        )
        mapper = Mapper(data_mapping)

        source = SourceData(data={})
        result = mapper(source)

        # Manually processed KEEP objects work
        assert isinstance(result, KeepTestTarget)
        assert result.processed_value == "processed_string"
        assert result.regular_value == "regular_string"

    def test_complex_transformation_with_a_b_data(self, test_A: dict[str, Any]) -> None:
        """Test complex transformation using A.json data structure."""

        def full_name_transform(data: dict) -> str:
            """Build full name from name parts."""
            first_name = get(data, "name.first", default="")
            given_names = get(data, "name.given", default=[])
            suffix = get(data, "name.suffix", default="")

            name_parts = [first_name] + given_names
            if suffix:
                name_parts.append(suffix)
            return " ".join(filter(None, name_parts))

        def current_address_transform(data: dict) -> str:
            """Format current address."""
            current_addr = get(data, "address.current", default={})
            street_lines = get(current_addr, "street", default=[])
            city = get(current_addr, "city", default="")
            state = get(current_addr, "state", default="")
            postal = get(current_addr, "postal_code", default="")
            country = get(current_addr, "country", default="")

            return "\n".join(
                filter(None, street_lines + [city, state, postal, country])
            )

        def last_previous_address_transform(data: dict) -> str:
            """Get last previous address."""
            previous_addrs = get(data, "address.previous", default=[])
            if not previous_addrs:
                return ""

            last_addr = previous_addrs[-1]
            prev_street = get(last_addr, "street", default=[])
            prev_city = get(last_addr, "city", default="")
            prev_state = get(last_addr, "state", default="")
            prev_postal = get(last_addr, "postal_code", default="")
            prev_country = get(last_addr, "country", default="")

            return "\n".join(
                filter(
                    None,
                    prev_street + [prev_city, prev_state, prev_postal, prev_country],
                )
            )

        mapping: dict[str, Any] = {
            "full_name": full_name_transform,
            "current_address": current_address_transform,
            "last_previous_address": last_previous_address_transform,
        }

        data_mapping = DataMapping(
            transformations=mapping,
            input_schema=ComplexPersonData,
            output_schema=FlatPersonData,
        )
        mapper = Mapper(data_mapping)

        source = ComplexPersonData.model_validate(test_A)
        result = mapper(source)

        assert isinstance(result, FlatPersonData)
        assert "Bob" in result.full_name
        assert "Figgens" in result.full_name
        assert "Sr." in result.full_name
        assert "123 Privet Drive" in result.current_address
        assert "Surrey" in result.current_address
