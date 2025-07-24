import pytest

import chidian.partials as p


def test_basic_arithmetic():
    """Test basic arithmetic operations."""
    n = 100
    assert p.add(1)(n) == n + 1
    assert p.subtract(1)(n) == n - 1
    assert p.multiply(10)(n) == n * 10
    assert p.divide(10)(n) == n / 10

    # Test with lists
    lst = [1, 2, 3]
    assert p.add([4])(lst) == lst + [4]


def test_boolean_checks():
    """Test basic boolean operations."""
    value = {"a": "b", "c": "d"}

    assert p.equals(value)(value) is True
    assert p.equals("test")("test") is True
    assert p.equals("test")("other") is False

    assert p.contains("a")(value) is True
    assert p.contains("z")(value) is False

    assert p.isinstance_of(dict)(value) is True
    assert p.isinstance_of(str)("test") is True
    assert p.isinstance_of(int)("test") is False


def test_basic_chainable_fn():
    """Test basic ChainableFunction functionality."""
    # Single operations
    assert p.upper("hello") == "HELLO"
    assert p.lower("WORLD") == "world"
    assert p.strip("  test  ") == "test"


def test_function_chain_creation():
    """Test creating FunctionChain with | operator."""
    # ChainableFunction | ChainableFunction
    chain = p.upper | p.replace(" ", "_")
    assert isinstance(chain, p.FunctionChain)
    assert len(chain) == 2
    assert chain("hello world") == "HELLO_WORLD"

    # Regular function | ChainableFunction
    chain2 = str.strip | p.upper
    assert chain2("  test  ") == "TEST"


def test_complex_chains():
    """Test complex function chains."""
    # Multi-step string transformation
    normalize = p.strip | p.lower | p.replace(" ", "_")
    assert normalize("  Hello World  ") == "hello_world"

    # Array operations
    get_last_word = p.split() | p.last | p.upper
    assert get_last_word("hello beautiful world") == "WORLD"

    # Mixed operations
    extract_number = p.split("-") | p.last | p.to_int | p.multiply(2)
    assert extract_number("item-42") == 84


def test_string_operations():
    """Test string manipulation functions."""
    # Split with custom separator
    split_comma = p.split(",")
    assert split_comma("a,b,c") == ["a", "b", "c"]

    # Replace with parameters
    sanitize = p.replace("&", "and") | p.replace("@", "at")
    assert sanitize("tom & jerry @ home") == "tom and jerry at home"

    # Join
    join_with_dash = p.join("-")
    assert join_with_dash(["a", "b", "c"]) == "a-b-c"


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
    parse_int = p.strip | p.to_int
    assert parse_int("  42  ") == 42

    # Number to string
    format_num = p.to_float | p.round_to(2) | p.to_str
    assert format_num("19.999") == "20.0"

    # Boolean conversion
    assert p.to_bool("") is False
    assert p.to_bool("text") is True
    assert p.to_bool(0) is False
    assert p.to_bool(1) is True


def test_get_operations():
    """Test get operations for data access."""
    data = {
        "user": {
            "name": "John",
            "age": 30,
            "emails": ["john@example.com", "john.doe@work.com"],
        }
    }

    # Basic get
    get_name = p.get("user.name")
    assert get_name(data) == "John"

    # Get with default
    get_missing = p.get("user.missing", default="N/A")
    assert get_missing(data) == "N/A"

    # Get from array
    get_email = p.get("user.emails[0]")
    assert get_email(data) == "john@example.com"

    # Chain with get
    get_upper_name = p.get("user.name") | p.upper
    assert get_upper_name(data) == "JOHN"


def test_default_handling():
    """Test default value handling."""
    # Replace None with default
    safe_upper = p.default_to("") | p.upper
    assert safe_upper(None) == ""
    assert safe_upper("hello") == "HELLO"

    # Chain with null safety
    safe_process = p.default_to("0") | p.to_int | p.add(10)
    assert safe_process(None) == 10
    assert safe_process("5") == 15


def test_numeric_operations():
    """Test numeric operations and rounding."""
    # Round to decimals
    round_2 = p.round_to(2)
    assert round_2(3.14159) == 3.14

    # Chain with arithmetic
    calculate = p.to_int | p.add(10) | p.multiply(2)
    assert calculate("5") == 30


def test_chain_composition():
    """Test composing multiple chains."""
    # Create reusable chains
    normalize_text = p.strip | p.lower

    # Compose chains
    process_input = normalize_text | p.replace(" ", "_") | p.upper
    assert process_input("  Hello World  ") == "HELLO_WORLD"

    # Chain of chains
    chain1 = p.upper | p.replace("A", "X")
    chain2 = p.replace("E", "Y") | p.lower
    combined = chain1 | chain2
    assert combined("apple") == "xpply"


def test_error_propagation():
    """Test that errors propagate through chains."""
    chain = p.to_int | p.multiply(2)

    with pytest.raises(ValueError):
        chain("not a number")

    # Safe handling with default - first convert to "0" then to int
    safe_chain = p.default_to("0") | p.to_int | p.multiply(2)
    assert safe_chain(None) == 0
    assert safe_chain("42") == 84


def test_function_chain_repr():
    """Test string representation of chains."""
    chain = p.upper | p.strip | p.replace(" ", "_")
    repr_str = repr(chain)
    assert "upper" in repr_str
    assert "strip" in repr_str
    assert "|" in repr_str


def test_real_world_usage():
    """Test realistic data transformation scenarios."""
    # Clean and format user input
    clean_input = p.strip | p.lower | p.replace(" ", "_")
    assert clean_input("  User Name  ") == "user_name"

    # Process numeric data
    process_score = p.to_float | p.round_to(1) | p.multiply(100) | p.to_int
    assert process_score("0.856") == 90

    # Extract and format
    extract_domain = p.split("@") | p.last | p.upper
    assert extract_domain("user@example.com") == "EXAMPLE.COM"

    # Complex nested data access
    data = {
        "users": [
            {"name": "  john doe  ", "score": "85.7"},
            {"name": "jane smith", "score": "92.3"},
        ]
    }

    get_first_user_score = (
        p.get("users[0].score") | p.to_float | p.round_to(0) | p.to_int
    )
    assert get_first_user_score(data) == 86
