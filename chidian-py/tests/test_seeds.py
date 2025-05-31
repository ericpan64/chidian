"""Consolidated tests for all SEED operations."""

import pytest
from chidian.seeds import DROP, KEEP, DropLevel


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






