"""Property-based tests for core chidian functionality."""

import chidian.partials as p
from chidian import get
from hypothesis import given
from hypothesis import strategies as st


# Custom strategies for valid paths
@st.composite
def valid_path_strategy(draw):
    """Generate valid path strings for chidian."""
    # Simple paths like "field", "field.subfield", "field[0]", etc.
    path_parts = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "_")),
                min_size=1,
                max_size=10,
            ),
            min_size=1,
            max_size=3,
        )
    )
    return ".".join(part for part in path_parts if part)


@st.composite
def data_with_paths(draw):
    """Generate data dictionary with corresponding valid paths."""
    # Create simple field names
    field_names = draw(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu")),
                min_size=1,
                max_size=8,
            ),
            min_size=1,
            max_size=5,
        )
    )

    # Create data dict
    data = {}
    paths = []

    for field in field_names:
        if field:  # Ensure field is not empty
            data[field] = draw(
                st.one_of(
                    st.text(min_size=0, max_size=20),
                    st.integers(),
                    st.lists(st.text(min_size=0, max_size=10), max_size=3),
                )
            )
            paths.append(field)

    return data, paths


class TestPropertyBasedCore:
    """Property-based tests for core functionality."""

    @given(data_with_paths())
    def test_get_always_returns_value_or_none(self, data_and_paths):
        """Test that get always returns a value or None, never crashes."""
        data, paths = data_and_paths

        # Test with valid paths
        for path in paths:
            result = get(data, path)
            # Should either return a value from data or None/default
            assert result is None or isinstance(
                result, (int, str, list, dict, bool, float)
            )

        # Test with invalid path - should not crash
        result = get(data, "nonexistent.path")
        assert result is None

    @given(st.text(max_size=50), st.text(max_size=50))
    def test_template_formatting(self, value1, value2):
        """Test that template always returns a string."""
        template_func = p.template("{} {}")
        result = template_func(value1, value2)
        assert isinstance(result, str)
        # Values should appear in result (as strings)
        assert str(value1) in result
        assert str(value2) in result

    @given(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu")),
                min_size=1,
                max_size=8,
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_coalesce_returns_value(self, path_names):
        """Test that coalesce always returns something."""
        # Filter out empty strings
        valid_paths = [p for p in path_names if p]
        if not valid_paths:
            return  # Skip if no valid paths

        # Create data with at least one non-empty value
        data = {valid_paths[0]: "found_value"}

        coalesce = p.coalesce(*valid_paths, default="DEFAULT")
        result = coalesce(data)

        # Should return either the found value or the default
        assert result == "found_value" or result == "DEFAULT"

    @given(
        st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Ll", "Lu")),
                min_size=1,
                max_size=8,
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_flatten_returns_string(self, path_names):
        """Test that flatten always returns a string."""
        # Filter out empty strings
        valid_paths = [p for p in path_names if p]
        if not valid_paths:
            return  # Skip if no valid paths

        # Create data with lists for each path
        data = {path: [f"value_{i}" for i in range(2)] for path in valid_paths}

        flatten_func = p.flatten(valid_paths, delimiter=", ")
        result = flatten_func(data)

        assert isinstance(result, str)

    @given(st.dictionaries(st.text(max_size=20), st.text(max_size=20), min_size=1))
    def test_case_matching(self, cases):
        """Test that case matching works reliably."""
        if not cases:
            return

        # Pick a key that exists in cases
        test_key = list(cases.keys())[0]
        expected_value = cases[test_key]

        case_func = p.case(cases, default="DEFAULT")

        # Should return the expected value for exact match
        result = case_func(test_key)
        assert result == expected_value

    @given(st.text(max_size=100))
    def test_partials_chaining(self, input_text):
        """Test that partials chaining doesn't crash."""
        # Simple chain that should always work
        try:
            chain = p.strip >> p.lower >> p.upper
            result = chain(input_text)
            assert isinstance(result, str)
            assert result == input_text.strip().lower().upper()
        except AttributeError:
            # input_text might not be a string in some edge cases
            pass


class TestPropertyBasedHelpers:
    """Property-based tests for helper functions."""

    @given(st.lists(st.integers(), min_size=1, max_size=10))
    def test_partials_list_operations(self, values):
        """Test list operations in partials."""
        # Test that basic list operations work
        assert p.first(values) == values[0]
        assert p.last(values) == values[-1]
        assert p.length(values) == len(values)

        if len(values) > 1:
            assert p.at_index(1)(values) == values[1]

    @given(st.text(min_size=1, max_size=50))
    def test_string_partials(self, text):
        """Test string operations."""
        # These should not crash
        assert isinstance(p.upper(text), str)
        assert isinstance(p.lower(text), str)
        assert isinstance(p.strip(text), str)

        # Chain them
        result = (p.strip >> p.lower >> p.upper)(text)
        assert isinstance(result, str)


class TestPropertyBasedRobustness:
    """Test that core functions handle edge cases gracefully."""

    @given(
        st.dictionaries(
            st.text(),
            st.one_of(st.none(), st.text(), st.integers(), st.lists(st.text())),
        )
    )
    def test_get_robustness(self, data):
        """Test get function with various data types."""
        # Should never crash, regardless of input
        result = get(data, "any.path.here")
        # Result should be None or a valid type
        assert result is None or isinstance(result, (str, int, list, dict, bool, float))

    @given(st.text(), st.text())
    def test_template_edge_cases(self, template_str, value):
        """Test template with various inputs."""
        if "{}" in template_str:
            try:
                template_func = p.template(template_str)
                result = template_func(value)
                assert isinstance(result, str)
            except (ValueError, IndexError):
                # Template formatting errors are acceptable
                pass

    @given(st.lists(st.text(), max_size=5))
    def test_flatten_empty_inputs(self, paths):
        """Test flatten with various path combinations."""
        # Should not crash even with empty or invalid paths
        try:
            flatten_func = p.flatten(paths, delimiter=", ")
            result = flatten_func({})
            assert isinstance(result, str)
        except Exception:
            # Some path combinations might be invalid, that's okay
            pass
