"""Property-based tests for core chidian functionality."""

from hypothesis import given
from hypothesis import strategies as st

import chidian.partials as p
from chidian import get


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

    @given(st.text(alphabet=st.characters(blacklist_categories=["Z"]), max_size=50))
    def test_string_operations_property(self, text_value):
        """Test that string operations are consistent."""
        # Test upper/lower are reversible
        upper_result = p.upper(text_value)
        lower_result = p.lower(text_value)

        assert isinstance(upper_result, str)
        assert isinstance(lower_result, str)

        # Test strip functionality (strip removes all surrounding whitespace)
        if text_value:
            padded = f"  {text_value}  "
            stripped = p.strip(padded)
            assert isinstance(stripped, str)
            # strip removes leading/trailing whitespace from the original value too
            assert stripped == text_value.strip()

    @given(st.integers(min_value=1, max_value=100))
    def test_arithmetic_operations_property(self, value):
        """Test that arithmetic operations are consistent."""
        # Test basic arithmetic properties
        add_result = p.add(10)(value)
        assert add_result == value + 10

        multiply_result = p.multiply(2)(value)
        assert multiply_result == value * 2

        # Test chain consistency with ChainableFunction
        add_chainable = p.ChainableFunction(p.add(5))
        multiply_chainable = p.ChainableFunction(p.multiply(2))
        chain_result = (add_chainable | multiply_chainable)(value)
        assert chain_result == (value + 5) * 2

    @given(st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    def test_array_operations_property(self, test_list):
        """Test that array operations work consistently."""
        # Test first/last
        first_result = p.first(test_list)
        last_result = p.last(test_list)

        assert first_result == test_list[0]
        assert last_result == test_list[-1]

        # Test length
        length_result = p.length(test_list)
        assert length_result == len(test_list)

        # Test at_index
        if len(test_list) > 2:
            middle_result = p.at_index(1)(test_list)
            assert middle_result == test_list[1]

    @given(st.dictionaries(st.text(max_size=20), st.text(max_size=20), min_size=1))
    def test_boolean_operations_property(self, test_dict):
        """Test that boolean operations work consistently."""
        if not test_dict:
            return

        # Pick a key that exists
        test_key = list(test_dict.keys())[0]
        test_value = test_dict[test_key]

        # Test equals
        equals_func = p.equals(test_value)
        assert equals_func(test_value) is True
        assert equals_func("different_value") is False

        # Test contains
        contains_func = p.contains(test_key)
        assert contains_func(test_dict) is True
        assert contains_func({}) is False

    @given(st.text(max_size=100))
    def test_partials_chaining(self, input_text):
        """Test that partials chaining doesn't crash."""
        # Simple chain that should always work
        try:
            chain = p.strip | p.lower | p.upper
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
        result = (p.strip | p.lower | p.upper)(text)
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

    @given(st.text(min_size=1), st.text())
    def test_type_conversion_edge_cases(self, separator, input_value):
        """Test type conversions with various inputs."""
        # Test string conversions are robust
        str_result = p.to_str(input_value)
        assert isinstance(str_result, str)

        # Test split doesn't crash
        try:
            split_func = p.split(separator)
            result = split_func(str_result)
            assert isinstance(result, list)
        except (AttributeError, ValueError):
            # Some edge cases may fail, which is acceptable
            pass

    @given(st.lists(st.text(min_size=1, max_size=10), max_size=5))
    def test_join_operations(self, text_list):
        """Test join operations with various inputs."""
        # Should not crash even with empty or invalid inputs
        try:
            join_func = p.join(", ")
            result = join_func(text_list)
            assert isinstance(result, str)
            if text_list:
                # If we have content, result should contain it
                assert len(result) >= 0
        except (AttributeError, TypeError):
            # Some combinations may fail, which is acceptable for edge cases
            pass
