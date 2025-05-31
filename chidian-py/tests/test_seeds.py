"""Consolidated tests for all SEED operations."""

import pytest
from chidian.seeds import DROP, KEEP, CASE, COALESCE, SPLIT, MERGE, FLATTEN, DropLevel


class TestDropKeep:
    """Test DROP and KEEP seeds."""
    
    def test_drop_levels(self):
        """Test DROP with different levels."""
        drop_this = DROP(DropLevel.THIS_OBJECT)
        drop_parent = DROP(DropLevel.PARENT)
        
        assert drop_this.level == DropLevel.THIS_OBJECT
        assert drop_parent.level == DropLevel.PARENT
        
        # Class methods
        assert DROP.this_object().level == DropLevel.THIS_OBJECT
        assert DROP.parent().level == DropLevel.PARENT
        
    def test_keep_basic(self):
        """Test KEEP preserves values."""
        keep = KEEP("test_value")
        assert keep.process({}) == "test_value"
        assert keep.value == "test_value"


class TestCase:
    """Test CASE seed."""
    
    @pytest.mark.parametrize("data,expected", [
        ({"status": "active"}, "ACTIVE"),
        ({"status": "inactive"}, "INACTIVE"),
        ({"status": "pending"}, "PENDING"),
        ({"status": "unknown"}, "DEFAULT"),
        ({"other": "field"}, "DEFAULT"),  # Missing status field
    ])
    def test_case_with_dict(self, data, expected):
        """Test CASE with dictionary of exact matches."""
        case = CASE(
            path="status",
            cases={
                "active": "ACTIVE",
                "inactive": "INACTIVE",
                "pending": "PENDING"
            },
            default="DEFAULT"
        )
        assert case.process(data) == expected
        assert case(data) == expected  # Test callable syntax
        
    def test_case_with_functions(self):
        """Test CASE with function conditions."""
        case = CASE(
            path="value",
            cases=[
                (lambda x: x > 100, "HIGH"),
                (lambda x: x > 50, "MEDIUM"),
                (lambda x: x > 0, "LOW"),
            ],
            default="ZERO_OR_NEGATIVE"
        )
        
        assert case({"value": 150}) == "HIGH"
        assert case({"value": 75}) == "MEDIUM"
        assert case({"value": 25}) == "LOW"
        assert case({"value": 0}) == "ZERO_OR_NEGATIVE"
        
    def test_case_no_default(self):
        """Test CASE without default returns None."""
        case = CASE(
            path="type",
            cases={"A": "Type A"}
        )
        assert case({"type": "B"}) is None


class TestTransformSeeds:
    """Test MERGE, FLATTEN, COALESCE, and SPLIT seeds."""
    
    def test_merge_basic(self):
        """Test MERGE with template."""
        merge = MERGE("first", "last", template="{} {}")
        data = {"first": "John", "last": "Doe"}
        assert merge.process(data) == "John Doe"
        
    def test_merge_skip_none(self):
        """Test MERGE skipping None values."""
        merge = MERGE("first", "middle", "last", template="{} {} {}", skip_none=True)
        data = {"first": "John", "middle": None, "last": "Doe"}
        # With skip_none=True, template should handle missing values
        result = merge.process(data)
        assert "None" not in result
        
    def test_coalesce_basic(self):
        """Test COALESCE returns first non-None value."""
        coalesce = COALESCE(["missing", "empty", "value"], default="DEFAULT")
        data = {
            "missing": None,
            "empty": "",
            "value": "found"
        }
        assert coalesce.process(data) == "found"
        assert coalesce(data) == "found"  # Test callable syntax
        
    def test_coalesce_all_none(self):
        """Test COALESCE returns default when all None."""
        coalesce = COALESCE(["a", "b", "c"], default="DEFAULT")
        assert coalesce({"a": None, "b": None, "c": None}) == "DEFAULT"
        
    def test_split_basic(self):
        """Test SPLIT extracts parts of strings."""
        split = SPLIT(path="email", pattern="@", part=0)
        data = {"email": "user@example.com"}
        assert split.process(data) == "user"
        assert split(data) == "user"  # Test callable syntax
        
    @pytest.mark.parametrize("part,expected", [
        (0, "user"),
        (1, "example.com"),
        (-1, "example.com"),
        (2, None),  # Out of bounds
        (-3, None),  # Out of bounds negative
    ])
    def test_split_parts(self, part, expected):
        """Test SPLIT with different part indices."""
        split = SPLIT(path="email", pattern="@", part=part)
        data = {"email": "user@example.com"}
        assert split(data) == expected
        
    def test_split_with_transform(self):
        """Test SPLIT with transformation function."""
        split = SPLIT(
            path="reference",
            pattern="/",
            part=-1,
            then=lambda x: int(x)
        )
        data = {"reference": "Patient/123"}
        assert split(data) == 123
        
    def test_flatten_basic(self):
        """Test FLATTEN joins values into string."""
        flatten = FLATTEN(["names", "ids"])
        data = {"names": ["John", "Jane"], "ids": ["123", "456"]}
        result = flatten.process(data)
        assert result == "John, Jane, 123, 456"
        
    def test_flatten_custom_delimiter(self):
        """Test FLATTEN with custom delimiter."""
        flatten = FLATTEN(["values"], delimiter=" | ")
        data = {"values": ["A", "B", "C"]}
        result = flatten(data)
        assert result == "A | B | C"
        
    def test_flatten_empty(self):
        """Test FLATTEN on empty or missing data."""
        flatten = FLATTEN(["empty", "missing"])
        assert flatten({"empty": []}) == ""
        assert flatten({}) == ""  # Missing paths


class TestSeedIntegration:
    """Test SEEDs working together."""
    
    def test_case_with_split(self):
        """Test combining CASE with SPLIT."""
        # First split email domain, then categorize
        split_domain = SPLIT(path="email", pattern="@", part=1)
        case_domain = CASE(
            path="domain",
            cases={
                "gmail.com": "PERSONAL",
                "company.com": "WORK",
                "edu": "ACADEMIC"
            },
            default="OTHER"
        )
        
        data = {"email": "user@gmail.com"}
        # In real usage, these would be composed in a mapping
        domain = split_domain(data)
        assert domain == "gmail.com"
        
    def test_coalesce_with_merge(self):
        """Test using COALESCE for flexible name handling."""
        # Coalesce to find any available name
        name_coalesce = COALESCE(
            ["preferred_name", "legal_name", "nickname"],
            default="Unknown"
        )
        
        data1 = {"legal_name": "John Doe", "nickname": "JD"}
        data2 = {"preferred_name": "Jane", "legal_name": "Jane Smith"}
        data3 = {}
        
        assert name_coalesce(data1) == "John Doe"
        assert name_coalesce(data2) == "Jane"
        assert name_coalesce(data3) == "Unknown"