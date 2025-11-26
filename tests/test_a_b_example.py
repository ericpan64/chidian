"""Tests demonstrating transformations between A.json and B.json formats."""

import json
from pathlib import Path

import pytest

from chidian import grab, mapper


class TestABTransformations:
    """Test transformations between A.json and B.json formats."""

    @pytest.fixture
    def a_data(self):
        """Load A.json test data."""
        path = Path(__file__).parent / "A.json"
        return json.loads(path.read_text())

    @pytest.fixture
    def b_data(self):
        """Load B.json test data."""
        path = Path(__file__).parent / "B.json"
        return json.loads(path.read_text())

    def test_a_to_b(self, a_data, b_data):
        """Transform nested A format to flat B format."""

        def format_address(addr):
            """Format address dict as multiline string."""
            parts = grab(addr, "street", default=[]) + [
                grab(addr, "city"),
                grab(addr, "postal_code"),
                grab(addr, "country"),
            ]
            return "\n".join(p for p in parts if p)

        @mapper
        def a_to_b(d):
            # Build full name from parts
            name_parts = [
                grab(d, "name.first"),
                *grab(d, "name.given", default=[]),
                grab(d, "name.suffix"),
            ]
            full_name = " ".join(p for p in name_parts if p)

            return {
                "full_name": full_name,
                "current_address": format_address(
                    grab(d, "address.current", default={})
                ),
                "last_previous_address": format_address(
                    grab(d, "address.previous[-1]", default={})
                ),
            }

        result = a_to_b(a_data)
        assert result == b_data

    def test_b_to_a(self, a_data, b_data):
        """Transform flat B format back to nested A format."""

        def parse_address(addr_str):
            """Parse multiline address string into components."""
            if not addr_str:
                return {}
            lines = addr_str.split("\n")
            # Last 3 lines are city, postal_code, country
            # Everything before is street
            return {
                "street": lines[:-3],
                "city": lines[-3] if len(lines) >= 3 else None,
                "postal_code": lines[-2] if len(lines) >= 2 else None,
                "country": lines[-1] if len(lines) >= 1 else None,
            }

        def parse_name(full_name):
            """Parse full name string into components."""
            if not full_name:
                return {}
            parts = full_name.split()
            # First part is first name, last part is suffix (if ends with .)
            # Middle parts are given names
            first = parts[0] if parts else None
            suffix = parts[-1] if parts and parts[-1].endswith(".") else None
            given = parts[1:-1] if suffix else parts[1:]
            return {
                "first": first,
                "given": given if given else None,
                "prefix": None,
                "suffix": suffix,
            }

        @mapper(remove_empty=False)
        def b_to_a(d):
            name = parse_name(grab(d, "full_name"))
            current = parse_address(grab(d, "current_address"))

            return {
                "name": name,
                "address": {
                    "current": current,
                    # Note: B format loses most previous addresses, we only have the last one
                    "previous": [parse_address(grab(d, "last_previous_address"))],
                },
            }

        result = b_to_a(b_data)

        # Verify key transformations work correctly
        assert result["name"]["first"] == "Bob"
        assert result["name"]["given"] == ["S", "Figgens"]
        assert result["name"]["suffix"] == "Sr."
        assert result["address"]["current"]["street"] == [
            "123 Privet Drive",
            "Little Whinging",
        ]
        assert result["address"]["current"]["city"] == "Surrey"
        assert result["address"]["previous"][0]["city"] == "London"

    def test_roundtrip_a_to_b_partial(self, a_data):
        """Test A -> B -> A preserves recoverable data."""

        def format_address(addr):
            parts = grab(addr, "street", default=[]) + [
                grab(addr, "city"),
                grab(addr, "postal_code"),
                grab(addr, "country"),
            ]
            return "\n".join(p for p in parts if p)

        def parse_address(addr_str):
            if not addr_str:
                return {}
            lines = addr_str.split("\n")
            return {
                "street": lines[:-3],
                "city": lines[-3] if len(lines) >= 3 else None,
                "postal_code": lines[-2] if len(lines) >= 2 else None,
                "country": lines[-1] if len(lines) >= 1 else None,
            }

        @mapper
        def a_to_b(d):
            name_parts = [
                grab(d, "name.first"),
                *grab(d, "name.given", default=[]),
                grab(d, "name.suffix"),
            ]
            return {
                "full_name": " ".join(p for p in name_parts if p),
                "current_address": format_address(
                    grab(d, "address.current", default={})
                ),
                "last_previous_address": format_address(
                    grab(d, "address.previous[-1]", default={})
                ),
            }

        @mapper(remove_empty=False)
        def b_to_a(d):
            parts = grab(d, "full_name", default="").split()
            return {
                "name": {
                    "first": parts[0] if parts else None,
                    "given": parts[1:-1]
                    if len(parts) > 2 and parts[-1].endswith(".")
                    else parts[1:],
                    "prefix": None,
                    "suffix": parts[-1] if parts and parts[-1].endswith(".") else None,
                },
                "address": {
                    "current": parse_address(grab(d, "current_address")),
                    "previous": [parse_address(grab(d, "last_previous_address"))],
                },
            }

        b_result = a_to_b(a_data)
        roundtrip = b_to_a(b_result)

        # Name should roundtrip perfectly
        assert roundtrip["name"]["first"] == a_data["name"]["first"]
        assert roundtrip["name"]["given"] == a_data["name"]["given"]
        assert roundtrip["name"]["suffix"] == a_data["name"]["suffix"]

        # Current address should roundtrip
        assert (
            roundtrip["address"]["current"]["city"]
            == a_data["address"]["current"]["city"]
        )

        # Only last previous address survives (B format limitation)
        assert len(roundtrip["address"]["previous"]) == 1
        assert (
            roundtrip["address"]["previous"][0]["city"]
            == a_data["address"]["previous"][-1]["city"]
        )
