"""Tests for the @mapper decorator and related functionality."""

import pytest

from chidian import DROP, KEEP, grab, mapper, mapping_context


class TestMapperBasic:
    """Test basic @mapper decorator functionality."""

    def test_simple_mapping(self):
        """Test basic mapper with grab."""

        @mapper
        def patient_summary(d):
            return {
                "patient_id": grab(d, "data.patient.id"),
                "is_active": grab(d, "data.patient.active"),
            }

        source = {"data": {"patient": {"id": "p-123", "active": True}}}
        result = patient_summary(source)

        assert result == {"patient_id": "p-123", "is_active": True}

    def test_nested_output(self):
        """Test mapper with nested output structure."""

        @mapper
        def with_nested(d):
            return {
                "patient": {
                    "id": grab(d, "data.id"),
                    "name": grab(d, "data.name"),
                },
                "meta": {"version": "1.0"},
            }

        source = {"data": {"id": "123", "name": "John"}}
        result = with_nested(source)

        assert result == {
            "patient": {"id": "123", "name": "John"},
            "meta": {"version": "1.0"},
        }

    def test_static_values(self):
        """Test mapper with static values."""

        @mapper
        def with_static(d):
            return {
                "version": "2.0",
                "type": "patient",
                "id": grab(d, "id"),
            }

        result = with_static({"id": "123"})
        assert result == {"version": "2.0", "type": "patient", "id": "123"}

    def test_composable_mappers(self):
        """Test that mappers can be composed."""

        @mapper
        def first_transform(d):
            return {"data": {"id": grab(d, "raw_id")}}

        @mapper
        def second_transform(d):
            return {"patient_id": grab(d, "data.id")}

        source = {"raw_id": "123"}
        result = second_transform(first_transform(source))

        assert result == {"patient_id": "123"}


class TestDrop:
    """Test DROP sentinel functionality."""

    def test_drop_this_object_in_dict(self):
        """Test DROP.THIS_OBJECT removes the containing dict."""

        @mapper
        def with_drop(d):
            return {
                "kept": {"id": grab(d, "id")},
                "dropped": {"trigger": DROP.THIS_OBJECT, "ignored": "x"},
            }

        result = with_drop({"id": "123"})
        assert result == {"kept": {"id": "123"}}

    def test_drop_this_object_in_list(self):
        """Test DROP.THIS_OBJECT in list removes just that item."""

        @mapper
        def filter_list(d):
            return {
                "tags": [
                    "first",
                    DROP.THIS_OBJECT,
                    "third",
                ]
            }

        result = filter_list({})
        assert result == {"tags": ["first", "third"]}

    def test_drop_nested_dict_in_list(self):
        """Test DROP.THIS_OBJECT in nested dict removes the dict from list."""

        @mapper
        def filter_list(d):
            return {
                "items": [
                    {"keep": "me"},
                    {"drop": DROP.THIS_OBJECT, "ignored": "x"},
                    {"also": "kept"},
                ]
            }

        result = filter_list({})
        assert result == {"items": [{"keep": "me"}, {"also": "kept"}]}

    def test_drop_parent(self):
        """Test DROP.PARENT removes the parent container."""

        @mapper
        def with_parent_drop(d):
            return {
                "kept": {"id": "123"},
                "items": [
                    {"trigger": DROP.PARENT},
                    {"ignored": "never seen"},
                ],
            }

        result = with_parent_drop({})
        assert result == {"kept": {"id": "123"}}

    def test_drop_grandparent(self):
        """Test DROP.GRANDPARENT removes two levels up."""

        @mapper
        def with_grandparent_drop(d):
            return {
                "outer": {
                    "middle": {"trigger": DROP.GRANDPARENT},
                }
            }

        result = with_grandparent_drop({})
        assert result == {}

    def test_drop_conditional(self):
        """Test conditional DROP based on data."""

        @mapper
        def conditional_drop(d):
            verified = grab(d, "verified")
            return {
                "id": grab(d, "id"),
                # Use nested dict so DROP.THIS_OBJECT removes only "sensitive" key
                "sensitive": {
                    "data": DROP.THIS_OBJECT if not verified else grab(d, "data"),
                },
            }

        # Not verified - sensitive dict is dropped (contains DROP)
        result = conditional_drop({"id": "123", "verified": False, "data": "secret"})
        assert result == {"id": "123"}

        # Verified - sensitive is kept
        result = conditional_drop({"id": "123", "verified": True, "data": "secret"})
        assert result == {"id": "123", "sensitive": {"data": "secret"}}


class TestKeep:
    """Test KEEP wrapper functionality."""

    def test_keep_empty_dict(self):
        """Test KEEP preserves empty dict."""

        @mapper
        def with_keep(d):
            return {
                "explicit_empty": KEEP({}),
                "implicit_empty": {},
            }

        result = with_keep({})
        assert result == {"explicit_empty": {}}

    def test_keep_none(self):
        """Test KEEP preserves None."""

        @mapper
        def with_keep(d):
            return {
                "explicit_none": KEEP(None),
                "implicit_none": None,
            }

        result = with_keep({})
        assert result == {"explicit_none": None}

    def test_keep_empty_list(self):
        """Test KEEP preserves empty list."""

        @mapper
        def with_keep(d):
            return {
                "explicit_empty": KEEP([]),
                "implicit_empty": [],
            }

        result = with_keep({})
        assert result == {"explicit_empty": []}

    def test_keep_empty_string(self):
        """Test KEEP preserves empty string."""

        @mapper
        def with_keep(d):
            return {
                "explicit_empty": KEEP(""),
                "implicit_empty": "",
            }

        result = with_keep({})
        assert result == {"explicit_empty": ""}


class TestEmptyRemoval:
    """Test automatic empty value removal."""

    def test_empty_values_removed_by_default(self):
        """Test empty values are removed by default."""

        @mapper
        def with_empties(d):
            return {
                "kept": "value",
                "empty_dict": {},
                "empty_list": [],
                "empty_string": "",
                "none_value": None,
            }

        result = with_empties({})
        assert result == {"kept": "value"}

    def test_remove_empty_false(self):
        """Test remove_empty=False keeps all values."""

        @mapper(remove_empty=False)
        def keep_empties(d):
            return {
                "kept": "value",
                "empty_dict": {},
                "empty_list": [],
                "none_value": None,
            }

        result = keep_empties({})
        assert result == {
            "kept": "value",
            "empty_dict": {},
            "empty_list": [],
            "none_value": None,
        }


class TestMappingContext:
    """Test mapping_context strict mode."""

    def test_normal_mode_missing_keys(self):
        """Test missing keys return None in normal mode."""

        @mapper
        def test_mapping(d):
            return {
                "exists": grab(d, "data.id"),
                "missing": grab(d, "does.not.exist"),
            }

        result = test_mapping({"data": {"id": "123"}})
        assert result == {"exists": "123"}  # 'missing' removed as None

    def test_strict_mode_raises_on_missing(self):
        """Test strict mode raises on missing keys."""

        @mapper
        def test_mapping(d):
            return {
                "exists": grab(d, "data.id"),
                "missing": grab(d, "does.not.exist"),
            }

        with pytest.raises(KeyError):
            with mapping_context(strict=True):
                test_mapping({"data": {"id": "123"}})

    def test_strict_mode_allows_existing_none(self):
        """Test strict mode allows keys that exist with None value."""

        @mapper(remove_empty=False)
        def test_mapping(d):
            return {
                "has_none": grab(d, "value"),
            }

        source = {"value": None}
        with mapping_context(strict=True):
            result = test_mapping(source)

        assert result == {"has_none": None}


class TestReadmeExamples:
    """Test examples from the README."""

    def test_quick_start_example(self):
        """Test the quick start example."""

        @mapper
        def patient_summary(d):
            return {
                "patient_id": grab(d, "data.patient.id"),
                "is_active": grab(d, "data.patient.active"),
                "latest_visit": grab(d, "data.visits[0].date"),
            }

        source = {
            "data": {
                "patient": {"id": "p-123", "active": True},
                "visits": [
                    {"date": "2024-01-15", "type": "checkup"},
                    {"date": "2024-02-20", "type": "followup"},
                ],
            }
        }

        result = patient_summary(source)
        assert result == {
            "patient_id": "p-123",
            "is_active": True,
            "latest_visit": "2024-01-15",
        }

    def test_normalize_user_example(self):
        """Test the normalize_user example pattern."""

        @mapper
        def normalize_user(d):
            return {
                "version": "2.0",
                "name": grab(d, "user.name"),
                "address": {
                    "city": grab(d, "location.city"),
                    "zip": grab(d, "location.postal"),
                },
            }

        source = {
            "user": {"name": "John"},
            "location": {"city": "Boston", "postal": "02101"},
        }

        result = normalize_user(source)
        assert result == {
            "version": "2.0",
            "name": "John",
            "address": {"city": "Boston", "zip": "02101"},
        }
