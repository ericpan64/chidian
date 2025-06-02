"""Consolidated tests for the Lexicon class."""

import pytest
from chidian.lexicon import Lexicon


class TestLexiconBasic:
    """Test basic Lexicon functionality."""

    @pytest.mark.parametrize(
        "mappings,forward_tests,reverse_tests",
        [
            # One-to-one mappings
            (
                {"8480-6": "271649006", "8462-4": "271650006"},
                [("8480-6", "271649006"), ("8462-4", "271650006")],
                [("271649006", "8480-6"), ("271650006", "8462-4")],
            ),
            # Many-to-one mappings
            (
                {("active", "current"): "A", ("inactive", "stopped"): "I"},
                [("active", "A"), ("current", "A"), ("inactive", "I")],
                [("A", "active"), ("I", "inactive")],  # First in tuple
            ),
        ],
    )
    def test_bidirectional_mappings(self, mappings, forward_tests, reverse_tests):
        """Test forward and reverse mappings."""
        lexicon = Lexicon(mappings)

        for key, expected in forward_tests:
            assert lexicon.forward(key) == expected
            assert lexicon[key] == expected

        for key, expected in reverse_tests:
            assert lexicon.reverse(key) == expected
            assert lexicon[key] == expected

    def test_default_handling(self):
        """Test default value behavior."""
        lexicon = Lexicon({"yes": "Y"}, default="UNKNOWN")

        assert lexicon["yes"] == "Y"
        assert lexicon["missing"] == "UNKNOWN"
        assert lexicon.get("missing", "CUSTOM") == "CUSTOM"

    def test_dict_interface(self):
        """Test that Lexicon works as a dict."""
        lexicon = Lexicon({"a": "1", "b": "2"})

        assert dict(lexicon) == {"a": "1", "b": "2"}
        assert list(lexicon.keys()) == ["a", "b"]
        assert "a" in lexicon
        assert "1" in lexicon  # Reverse lookup

    def test_empty_lexicon(self):
        """Test empty lexicon behavior."""
        lexicon = Lexicon({})

        assert len(lexicon) == 0
        assert lexicon.forward("any") is None
        with pytest.raises(KeyError):
            _ = lexicon["any"]


class TestLexiconRealWorld:
    """Test real-world healthcare code mapping scenarios."""

    def test_medical_code_mapping(self):
        """Test LOINC to SNOMED mapping example."""
        lab_codes = Lexicon(
            {
                "8480-6": "271649006",  # Systolic BP
                ("2160-0", "38483-4"): "113075003",  # Creatinine variants
            },
            metadata={"version": "2023-Q4"},
        )

        # Forward mapping
        assert lab_codes["8480-6"] == "271649006"
        assert lab_codes["2160-0"] == "113075003"
        assert lab_codes["38483-4"] == "113075003"

        # Reverse mapping
        assert lab_codes["271649006"] == "8480-6"
        assert lab_codes["113075003"] == "2160-0"  # First in tuple

        # Metadata
        assert lab_codes.metadata["version"] == "2023-Q4"
        assert lab_codes.can_reverse() is True
