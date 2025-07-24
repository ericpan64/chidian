"""Tests for the Lexicon class with tuple support."""

import pytest

from chidian.lexicon import Lexicon


class TestLexiconBasic:
    """Test basic Lexicon functionality."""

    def test_simple_string_mappings(self):
        """Test basic one-to-one string mappings."""
        lexicon = Lexicon({"8480-6": "271649006", "8462-4": "271650006"})

        # Forward lookups (keys first)
        assert lexicon["8480-6"] == "271649006"
        assert lexicon["8462-4"] == "271650006"

        # Reverse lookups (values second)
        assert lexicon["271649006"] == "8480-6"
        assert lexicon["271650006"] == "8462-4"

    def test_tuple_many_to_one_mappings(self):
        """Test many-to-one mappings with tuples."""
        lexicon = Lexicon(
            {
                ("A", "B", "C"): "x",
                ("D", "E"): "y",
                "F": "z",  # Can mix single and tuple mappings
            }
        )

        # Forward lookups - all keys map to value
        assert lexicon["A"] == "x"
        assert lexicon["B"] == "x"
        assert lexicon["C"] == "x"
        assert lexicon["D"] == "y"
        assert lexicon["E"] == "y"
        assert lexicon["F"] == "z"

        # Reverse lookups - first in tuple is default
        assert lexicon["x"] == "A"  # First in tuple
        assert lexicon["y"] == "D"  # First in tuple
        assert lexicon["z"] == "F"

    def test_lookup_priority(self):
        """Test that keys are scanned before values."""
        # If a value matches a key, the key lookup wins
        lexicon = Lexicon({"A": "B", "B": "C"})

        assert lexicon["A"] == "B"  # Key lookup
        assert lexicon["B"] == "C"  # Key lookup (takes priority over value)
        assert lexicon["C"] == "B"  # Value lookup (reverse)

    def test_get_method(self):
        """Test get method with defaults."""
        lexicon = Lexicon(
            {
                "yes": "Y",
                "no": "N",
                ("true", "1", "on"): "T",
                ("false", "0", "off"): "F",
            }
        )

        # Key lookups
        assert lexicon.get("yes") == "Y"
        assert lexicon.get("true") == "T"
        assert lexicon.get("1") == "T"

        # Value lookups (reverse)
        assert lexicon.get("Y") == "yes"
        assert lexicon.get("T") == "true"  # First in tuple
        assert lexicon.get("F") == "false"  # First in tuple

        # Missing keys with default
        assert lexicon.get("missing") is None
        assert lexicon.get("missing", "DEFAULT") == "DEFAULT"

    def test_instance_default(self):
        """Test default value behavior."""
        lexicon = Lexicon({"yes": "Y"}, default="UNKNOWN")

        assert lexicon["yes"] == "Y"
        assert lexicon["Y"] == "yes"
        assert lexicon["missing"] == "UNKNOWN"
        assert lexicon.get("missing") == "UNKNOWN"
        assert lexicon.get("missing", "CUSTOM") == "CUSTOM"  # Override default

    def test_contains(self):
        """Test membership checking."""
        lexicon = Lexicon({"a": "1", ("b", "c"): "2"})

        # Keys
        assert "a" in lexicon
        assert "b" in lexicon
        assert "c" in lexicon

        # Values (also searchable)
        assert "1" in lexicon
        assert "2" in lexicon

        # Missing
        assert "d" not in lexicon
        assert "3" not in lexicon

    def test_dict_interface(self):
        """Test that Lexicon maintains dict-like interface."""
        lexicon = Lexicon({"a": "1", "b": "2"})

        # Basic dict operations
        assert len(lexicon) == 2
        assert sorted(lexicon.keys()) == ["a", "b"]
        assert sorted(lexicon.values()) == ["1", "2"]
        assert dict(lexicon) == {"a": "1", "b": "2"}

    def test_empty_lexicon(self):
        """Test empty lexicon behavior."""
        lexicon = Lexicon({})

        assert len(lexicon) == 0
        assert lexicon.get("any") is None

        with pytest.raises(KeyError):
            _ = lexicon["any"]

    def test_no_key_error_with_default(self):
        """Test that KeyError is not raised when default is set."""
        lexicon = Lexicon({}, default="DEFAULT")

        # Should return default, not raise KeyError
        assert lexicon["missing"] == "DEFAULT"


class TestLexiconBuilder:
    """Test the builder pattern interface."""

    def test_builder_basic(self):
        """Test basic builder usage."""
        lexicon = Lexicon.builder().add("A", "1").add("B", "2").build()

        assert lexicon["A"] == "1"
        assert lexicon["B"] == "2"
        assert lexicon["1"] == "A"
        assert lexicon["2"] == "B"

    def test_builder_with_many(self):
        """Test builder with many-to-one mappings."""
        lexicon = (
            Lexicon.builder()
            .add_many(["A", "B", "C"], "x")
            .add_many(["D", "E"], "y")
            .add("F", "z")
            .build()
        )

        # Forward mappings
        assert lexicon["A"] == "x"
        assert lexicon["B"] == "x"
        assert lexicon["C"] == "x"
        assert lexicon["F"] == "z"

        # Reverse mappings (first is default)
        assert lexicon["x"] == "A"
        assert lexicon["y"] == "D"
        assert lexicon["z"] == "F"

    def test_builder_with_default(self):
        """Test builder with default value."""
        lexicon = Lexicon.builder().add("A", "1").set_default("MISSING").build()

        assert lexicon["A"] == "1"
        assert lexicon["missing"] == "MISSING"

    def test_builder_with_metadata(self):
        """Test builder with metadata."""
        lexicon = (
            Lexicon.builder().add("A", "1").set_metadata({"version": "1.0"}).build()
        )

        assert lexicon.metadata["version"] == "1.0"

    def test_builder_primary_override(self):
        """Test that builder can override primary reverse mapping."""
        lexicon = (
            Lexicon.builder()
            .add_many(["A", "B", "C"], "x")
            .set_primary_reverse("x", "B")  # Override default
            .build()
        )

        assert lexicon["x"] == "B"  # Not "A"


class TestLexiconEdgeCases:
    """Test edge cases and special scenarios."""

    def test_self_mapping(self):
        """Test when a key maps to itself."""
        lexicon = Lexicon({"A": "A", "B": "B"})

        # Should work normally
        assert lexicon["A"] == "A"
        assert lexicon["B"] == "B"

    def test_circular_mapping(self):
        """Test circular mappings."""
        lexicon = Lexicon({"A": "B", "B": "A"})

        # Forward lookups
        assert lexicon["A"] == "B"
        assert lexicon["B"] == "A"

    def test_chain_mapping(self):
        """Test chain-like mappings."""
        lexicon = Lexicon({"A": "B", "B": "C", "C": "D"})

        # Each lookup is independent
        assert lexicon["A"] == "B"
        assert lexicon["B"] == "C"
        assert lexicon["C"] == "D"
        assert lexicon["D"] == "C"  # Reverse lookup

    def test_case_sensitivity(self):
        """Test that lookups are case-sensitive."""
        lexicon = Lexicon({"Code": "VALUE", "code": "value"})

        assert lexicon["Code"] == "VALUE"
        assert lexicon["code"] == "value"
        assert lexicon["VALUE"] == "Code"
        assert lexicon["value"] == "code"

    def test_whitespace_handling(self):
        """Test handling of whitespace in keys/values."""
        lexicon = Lexicon({" A ": " B ", "C": "D "})

        assert lexicon[" A "] == " B "
        assert lexicon[" B "] == " A "
        assert lexicon["C"] == "D "
        assert lexicon["D "] == "C"

    def test_overlapping_tuples(self):
        """Test when multiple tuples map to same value."""
        lexicon = Lexicon(
            {
                ("A", "B"): "x",
                ("C", "D"): "x",  # Same value
                "E": "x",  # Also same value
            }
        )

        # All forward mappings work
        assert lexicon["A"] == "x"
        assert lexicon["B"] == "x"
        assert lexicon["C"] == "x"
        assert lexicon["D"] == "x"
        assert lexicon["E"] == "x"

        # Reverse gives first occurrence
        assert lexicon["x"] == "A"  # First key that mapped to "x"

    def test_empty_tuple(self):
        """Test that empty tuples are handled gracefully."""
        with pytest.raises(ValueError, match="Empty tuple"):
            Lexicon({(): "value"})

    def test_mixed_types_rejected(self):
        """Test that non-string types are rejected."""
        with pytest.raises(TypeError, match="must be strings"):
            Lexicon({123: "value"})

        with pytest.raises(TypeError, match="must be strings"):
            Lexicon({"key": 456})

        with pytest.raises(TypeError, match="must be strings"):
            Lexicon({("A", 123): "value"})


class TestLexiconRealWorld:
    """Test real-world scenarios."""

    def test_medical_code_mapping(self):
        """Test LOINC to SNOMED mapping example."""
        lab_codes = Lexicon(
            {
                "8480-6": "271649006",  # Systolic BP
                "8462-4": "271650006",  # Diastolic BP
                "8867-4": "364075005",  # Heart rate
                # Multiple LOINC codes for same concept
                ("2160-0", "38483-4", "14682-9"): "113075003",  # Creatinine
            },
            metadata={"version": "2023-Q4", "source": "LOINC-SNOMED"},
        )

        # Forward mapping (LOINC to SNOMED)
        assert lab_codes["8480-6"] == "271649006"
        assert lab_codes["2160-0"] == "113075003"
        assert lab_codes["38483-4"] == "113075003"
        assert lab_codes["14682-9"] == "113075003"

        # Reverse mapping (SNOMED to LOINC)
        assert lab_codes["271649006"] == "8480-6"
        assert lab_codes["113075003"] == "2160-0"  # First in tuple

        # Metadata
        assert lab_codes.metadata["version"] == "2023-Q4"

    def test_status_code_mapping(self):
        """Test status code transformations with aliases."""
        status_map = Lexicon(
            {
                ("active", "current", "live"): "A",
                ("inactive", "stopped", "discontinued"): "I",
                ("pending", "waiting"): "P",
                "completed": "C",
            },
            default="U",  # Unknown
        )

        # Forward mapping with aliases
        assert status_map["active"] == "A"
        assert status_map["current"] == "A"
        assert status_map["live"] == "A"
        assert status_map["stopped"] == "I"
        assert status_map["completed"] == "C"

        # Reverse mapping (first alias is default)
        assert status_map["A"] == "active"
        assert status_map["I"] == "inactive"
        assert status_map["P"] == "pending"

        # Unknown status
        assert status_map["unknown"] == "U"
        assert status_map["X"] == "U"

    def test_unit_conversion_codes(self):
        """Test unit of measure mappings."""
        unit_map = Lexicon(
            {
                ("mg/dL", "mg/dl", "MG/DL"): "MG_PER_DL",
                ("mmol/L", "mmol/l", "MMOL/L"): "MMOL_PER_L",
                "g/dL": "G_PER_DL",
                "mEq/L": "MEQ_PER_L",
            }
        )

        # Case variations all map to canonical form
        assert unit_map["mg/dL"] == "MG_PER_DL"
        assert unit_map["mg/dl"] == "MG_PER_DL"
        assert unit_map["MG/DL"] == "MG_PER_DL"

        # Reverse gives the first (preferred) form
        assert unit_map["MG_PER_DL"] == "mg/dL"
        assert unit_map["MMOL_PER_L"] == "mmol/L"
