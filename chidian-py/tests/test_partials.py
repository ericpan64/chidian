from copy import deepcopy

import chidian.partials as p
import pytest


def test_generic_apply_wrappers() -> None:
    n = 100
    assert p.add(1)(n) == n + 1
    assert p.subtract(1)(n) == n - 1
    assert p.subtract(1, before=True)(n) == 1 - n
    assert p.multiply(10)(n) == n * 10
    assert p.divide(10)(n) == n / 10
    assert p.divide(10, before=True)(n) == 10 / n

    lst = [1, 2, 3]
    assert p.add([4])(lst) == lst + [4]
    assert p.add([4], before=True)(lst) == [4] + lst

    f = 4.2
    assert p.multiply(3)(f) == 3 * f
    assert p.multiply(3, before=True)(f * f) == (f * f) * 3


def test_generic_conditional_wrappers() -> None:
    value = {"a": "b", "c": "d"}
    copied_value = deepcopy(value)
    example_key = "a"

    assert p.equals(copied_value)(value) == (value == copied_value)
    assert p.not_equal(copied_value)(value) == (value != copied_value)
    assert p.equivalent(copied_value)(value) == (value is copied_value)
    assert p.not_equivalent(copied_value)(value) == (value is not copied_value)
    assert p.contains(example_key)(copied_value) == (example_key in value)
    assert p.not_contains(example_key)(copied_value) == (example_key not in value)
    assert p.contained_in(copied_value)(example_key) == (example_key in value)
    assert p.not_contained_in(copied_value)(example_key) == (example_key not in value)
    assert p.isinstance_of(dict)(value) == isinstance(value, dict)
    assert p.isinstance_of(str)(example_key) == isinstance(example_key, str)


def test_iterable_wrappers() -> None:
    supported_iterables = ([1, 2, 3, 4, 5], (1, 2, 3, 4, 5))
    for value in supported_iterables:
        assert p.keep(1)(value) == value[:1]
        assert p.keep(50)(value) == value[:50]
        assert p.index(0)(value) == value[0]
        assert p.index(1)(value) == value[1]
        assert p.index(-1)(value) == value[-1]
        assert p.index(-3)(value) == value[-3]


def test_stdlib_wrappers() -> None:
    EXAMPLE_LIST = ["a", "b", "c"]
    assert p.map_to_list(str.upper)(EXAMPLE_LIST) == ["A", "B", "C"]
    assert p.filter_to_list(p.equals("a"))(EXAMPLE_LIST) == ["a"]


def test_basic_chainable_fn():
    """Test basic ChainableFn functionality."""
    # Single operation
    assert p.upper("hello") == "HELLO"
    assert p.lower("WORLD") == "world"

    # Check it preserves function behavior
    assert p.strip("  test  ") == "test"
    assert p.capitalize("hello world") == "Hello world"


def test_function_chain_creation():
    """Test creating FunctionChain with >> operator."""
    # ChainableFn >> ChainableFn
    chain = p.upper >> p.replace(" ", "_")
    assert isinstance(chain, p.FunctionChain)
    assert len(chain) == 2
    assert chain("hello world") == "HELLO_WORLD"

    # Regular function >> ChainableFn
    chain2 = str.strip >> p.upper
    assert chain2("  test  ") == "TEST"

    # ChainableFn >> regular function
    chain3 = p.lower >> str.title
    assert chain3("HELLO WORLD") == "Hello World"


def test_complex_chains():
    """Test complex function chains."""
    # Multi-step string transformation
    normalize = p.strip >> p.lower >> p.replace(" ", "_") >> p.replace("-", "_")
    assert normalize("  Hello-World  ") == "hello_world"

    # Array operations
    get_last_word = p.split() >> p.last >> p.upper
    assert get_last_word("hello beautiful world") == "WORLD"

    # Mixed operations
    extract_number = p.split("-") >> p.last >> p.to_int >> p.multiply(10)
    assert extract_number("item-42") == 420


def test_parameterized_chainable_fns():
    """Test ChainableFn factories with parameters."""
    # Split with custom separator
    split_comma = p.split(",")
    assert split_comma("a,b,c") == ["a", "b", "c"]

    # Replace with parameters
    sanitize = p.replace("&", "and") >> p.replace("@", "at")
    assert sanitize("tom & jerry @ home") == "tom and jerry at home"

    # Round to decimals
    round_2 = p.round_to(2)
    assert round_2(3.14159) == 3.14

    # Chain with parameters
    process = p.to_float >> p.round_to(1) >> p.to_str
    assert process("3.456") == "3.5"


def test_array_operations():
    """Test array/list operations."""
    data = ["first", "second", "third", "fourth"]

    assert p.first(data) == "first"
    assert p.last(data) == "fourth"
    assert p.length(data) == 4
    assert p.at_index(2)(data) == "third"
    assert p.slice_range(1, 3)(data) == ["second", "third"]

    # Empty list handling
    assert p.first([]) is None
    assert p.last([]) is None
    assert p.at_index(10)([1, 2, 3]) is None


def test_type_conversions():
    """Test type conversion chains."""
    # String to number
    parse_int = p.strip >> p.to_int
    assert parse_int("  42  ") == 42

    # Number to formatted string
    format_price = p.to_float >> p.round_to(2) >> p.format_string("${}")
    assert format_price("19.999") == "$20.0"

    # Boolean conversion
    truthiness = p.lower >> p.equals("yes")
    assert truthiness("YES")
    assert not truthiness("no")


def test_fhir_specific_operations():
    """Test FHIR-specific transformations."""
    # Extract ID from reference
    assert p.extract_id()("Patient/123") == "123"
    assert p.extract_id()("Observation/obs-456") == "obs-456"
    assert p.extract_id()("789") == "789"  # No slash

    # Complex FHIR reference processing
    get_patient_id = p.extract_id() >> p.to_int >> p.format_string("PAT-{:04d}")
    assert get_patient_id("Patient/42") == "PAT-0042"


def test_default_handling():
    """Test default value handling."""
    # Replace None with default
    safe_upper = p.default_to("") >> p.upper
    assert safe_upper(None) == ""
    assert safe_upper("hello") == "HELLO"

    # Chain with null safety
    safe_process = p.default_to("0") >> p.to_int >> p.add(10)
    assert safe_process(None) == 10
    assert safe_process("5") == 15


def test_chain_composition():
    """Test composing multiple chains."""
    # Create reusable chains
    normalize_name = p.strip >> p.lower >> p.capitalize

    # Compose chains
    process_title = normalize_name >> p.format_string("Title: {}")
    assert process_title("  john DOE  ") == "Title: John doe"

    # Chain of chains
    chain1 = p.upper >> p.replace("A", "X")
    chain2 = p.replace("E", "Y") >> p.lower
    combined = chain1 >> chain2
    assert combined("apple") == "xpply"


def test_with_existing_partials():
    """Test integration with existing partial functions."""
    # Use existing arithmetic partials
    calculate = p.to_int >> p.add(10) >> p.multiply(2)
    assert calculate("5") == 30

    # Mix with new chainable functions
    process = p.strip >> p.to_int >> p.ChainableFn(lambda x: x > 10)
    assert process("  15  ")
    assert not process("  5  ")


def test_error_propagation():
    """Test that errors propagate through chains."""
    chain = p.to_int >> p.multiply(2)

    with pytest.raises(ValueError):
        chain("not a number")

    # But we can add error handling
    safe_chain = p.ChainableFn(lambda x: int(x) if x.isdigit() else 0) >> p.multiply(2)
    assert safe_chain("42") == 84
    assert safe_chain("abc") == 0


def test_function_chain_repr():
    """Test string representation of chains."""
    chain = p.upper >> p.strip >> p.replace(" ", "_")
    repr_str = repr(chain)
    assert "upper" in repr_str
    assert "strip" in repr_str
    assert ">>" in repr_str


# Tests for new partials that replaced SEEDs
def test_case_partial():
    """Test case partial function."""
    # Test with dict cases
    status_mapper = p.case(
        {"active": "✓ Active", "inactive": "✗ Inactive"}, default="Unknown"
    )

    assert status_mapper("active") == "✓ Active"
    assert status_mapper("inactive") == "✗ Inactive"
    assert status_mapper("pending") == "Unknown"

    # Test with function cases
    range_mapper = p.case(
        [
            (lambda x: x > 100, "HIGH"),
            (lambda x: x > 50, "MEDIUM"),
            (lambda x: x >= 0, "LOW"),
        ],
        default="INVALID",
    )

    assert range_mapper(150) == "HIGH"
    assert range_mapper(75) == "MEDIUM"
    assert range_mapper(25) == "LOW"
    assert range_mapper(-10) == "INVALID"


def test_coalesce_partial():
    """Test coalesce partial function."""

    data = {"missing": None, "empty": "", "value": "found", "backup": "backup_value"}

    # Test with multiple paths
    coalesce_found_key = p.coalesce("missing", "empty", "value", default="DEFAULT")
    assert coalesce_found_key(data) == "found"

    # Test with all None/empty
    coalesce_empty = p.coalesce("missing", "empty", default="DEFAULT")
    assert coalesce_empty(data) == "DEFAULT"

    # Test without default
    coalesce_no_default = p.coalesce("value", "backup")
    assert coalesce_no_default(data) == "found"


def test_template_partial():
    """Test template partial function."""
    # Basic template
    name_template = p.template("{} {}")
    assert name_template("John", "Doe") == "John Doe"

    # Template with skip_none
    full_template = p.template("{} {} {}", skip_none=True)
    assert full_template("John", None, "Doe") == "John Doe"
    assert full_template("John", "Middle", "Doe") == "John Middle Doe"
    assert full_template(None, None, None) == ""


def test_flatten_partial():
    """Test flatten partial function."""
    data = {
        "names": ["John", "Jane"],
        "ids": ["123", "456"],
        "empty": [],
        "single": "solo",
    }

    # Test basic flatten
    flatten_func = p.flatten(["names", "ids"])
    result = flatten_func(data)
    assert result == "John, Jane, 123, 456"

    # Test custom delimiter
    flatten_pipe = p.flatten(["names"], delimiter=" | ")
    assert flatten_pipe(data) == "John | Jane"

    # Test with empty and single values
    flatten_mixed = p.flatten(["names", "empty", "single"])
    assert flatten_mixed(data) == "John, Jane, solo"


def test_partials_integration_with_chains():
    """Test that new partials work with function chains."""
    # Chain case with other operations
    status_chain = (
        p.get("status")
        >> p.case({"1": "active", "0": "inactive"}, default="unknown")
        >> p.upper
    )
    data = {"status": "1"}
    assert status_chain(data) == "ACTIVE"

    # Use template in a complex chain
    format_name = p.template("{} {}")
    name_chain = (
        p.ChainableFn(
            lambda data: format_name(p.get("first")(data), p.get("last")(data))
        )
        >> p.upper
    )

    name_data = {"first": "john", "last": "doe"}
    assert name_chain(name_data) == "JOHN DOE"
