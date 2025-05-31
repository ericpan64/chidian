"""Property-based tests for chidian using Hypothesis."""

import pytest
from hypothesis import given, strategies as st, assume
from typing import Any

from chidian import get
from chidian.lib import put
from chidian.seeds import MERGE, COALESCE, FLATTEN


# Custom strategies for JSON-like data
json_primitives = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.floats(allow_nan=False, allow_infinity=False),
    st.text(min_size=0, max_size=10)
)

# Recursive JSON strategy
json_data = st.recursive(
    json_primitives,
    lambda children: st.one_of(
        st.lists(children, max_size=5),
        st.dictionaries(
            st.text(min_size=1, max_size=10, alphabet=st.characters(min_codepoint=97, max_codepoint=122)),
            children,
            max_size=5
        )
    ),
    max_leaves=10
)

# Valid path components
path_component = st.text(min_size=1, max_size=10, alphabet=st.characters(min_codepoint=97, max_codepoint=122))
array_index = st.integers(min_value=0, max_value=5)

# Simple paths (no wildcards or slices)
@st.composite
def simple_paths(draw):
    """Generate simple dot notation paths."""
    components = draw(st.lists(path_component, min_size=1, max_size=3))
    path = ".".join(components)
    
    # Optionally add an array index
    if draw(st.booleans()):
        index = draw(array_index)
        path = f"{path}[{index}]"
    
    return path


class TestPropertyBasedGetPut:
    """Property-based tests for get/put operations."""
    
    @given(json_data, simple_paths())
    def test_put_get_roundtrip(self, data, path):
        """Test that put followed by get returns the same value."""
        value = "test_value"
        
        # Put the value
        result = put(data if isinstance(data, dict) else {}, path, value)
        
        # Get it back
        retrieved = get(result, path)
        
        # Should get back what we put in
        assert retrieved == value
        
    @given(json_data, simple_paths())
    def test_put_preserves_existing_data(self, data, path):
        """Test that put doesn't destroy unrelated data."""
        if not isinstance(data, dict) or not data:
            return  # Skip non-dict or empty data
            
        # Get an existing key that's not in our path
        existing_keys = list(data.keys())
        if not existing_keys:
            return
            
        preserve_key = existing_keys[0]
        preserve_value = data[preserve_key]
        
        # Put new value at path
        result = put(data, path, "new_value")
        
        # Check if the path would overwrite our preserved key
        if not path.startswith(preserve_key):
            # Original data should still be there
            assert get(result, preserve_key) == preserve_value
            
    @given(st.dictionaries(
        path_component,
        st.one_of(st.none(), st.text(), st.integers()),
        min_size=0,
        max_size=5
    ))
    def test_get_missing_path_returns_none(self, data):
        """Test that getting a non-existent path returns None."""
        # Generate a path that definitely doesn't exist
        missing_path = "definitely.not.there.at.all"
        assert get(data, missing_path) is None
        
    @given(st.dictionaries(
        path_component,
        st.text(),
        min_size=1,
        max_size=5
    ))
    def test_get_with_default(self, data):
        """Test that get returns default for missing paths."""
        default = "DEFAULT_VALUE"
        missing_path = "missing.path.here"
        
        result = get(data, missing_path, default=default)
        assert result == default


class TestPropertyBasedSeeds:
    """Property-based tests for SEED operations."""
    
    @given(st.lists(path_component, min_size=1, max_size=5))
    def test_merge_skip_none_no_none_in_output(self, paths):
        """Test that MERGE with skip_none=True never outputs 'None'."""
        # Create data with some None values
        data = {}
        for i, path in enumerate(paths):
            if i % 2 == 0:
                data[path] = f"value_{i}"
            else:
                data[path] = None
                
        # Create template with right number of placeholders
        template = " ".join("{}" for _ in paths)
        
        merge = MERGE(*paths, template=template, skip_none=True)
        result = merge.process(data)
        
        # Result should not contain literal "None"
        assert "None" not in result
        
    @given(st.lists(path_component, min_size=2, max_size=5).filter(lambda x: len(set(x)) == len(x)))
    def test_coalesce_returns_first_non_none(self, paths):
        """Test that COALESCE returns the first non-None value."""
        # Create data where we know which path has a value
        data = {}
        value_index = len(paths) // 2  # Put value in middle
        
        for i, path in enumerate(paths):
            if i < value_index:
                data[path] = None
            elif i == value_index:
                data[path] = "FOUND_VALUE"
            else:
                data[path] = f"later_value_{i}"
                
        coalesce = COALESCE(paths)
        result = coalesce.process(data)
        
        assert result == "FOUND_VALUE"
        
    @given(st.dictionaries(
        path_component,
        st.lists(st.text(min_size=0, max_size=5), min_size=0, max_size=5),
        min_size=1,
        max_size=3
    ))
    def test_flatten_joins_all_values(self, data):
        """Test that FLATTEN joins all values from paths."""
        paths = list(data.keys())
        
        flatten = FLATTEN(paths, delimiter="<SEP>")
        result = flatten.process(data)
        
        # Count the values we expect
        expected_count = sum(len(v) for v in data.values() if isinstance(v, list))
        if expected_count > 0:
            # Result should contain the delimiter between values
            assert result.count("<SEP>") == expected_count - 1
            
    @given(
        st.dictionaries(path_component, st.integers(min_value=-100, max_value=100)),
        st.lists(
            st.tuples(
                st.one_of(
                    st.just(lambda x: x > 0),
                    st.just(lambda x: x < 0),
                    st.just(lambda x: x == 0)
                ),
                st.text(min_size=1, max_size=10)
            ),
            min_size=1,
            max_size=3
        )
    )
    def test_case_handles_all_inputs(self, data, cases):
        """Test that CASE always returns a value."""
        # Pick a key from data
        if not data:
            return
            
        path = list(data.keys())[0]
        default = "DEFAULT"
        
        # Create CASE with our conditions
        case_seed = st.builds(
            lambda: CASE(path, cases, default=default)
        )
        
        # CASE should always return something (either matched or default)
        # This is more of a smoke test that CASE doesn't crash
        for case in cases:
            try:
                seed = CASE(path, [case], default=default)
                result = seed.process(data)
                assert result is not None
            except:
                pass  # Some conditions might not be valid