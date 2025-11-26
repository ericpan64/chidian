"""
Tests for chidian.validation module.
"""

import pytest

from chidian.validation import (
    Between,
    DictV,
    Err,
    Gt,
    Gte,
    InRange,
    InSet,
    IsType,
    ListV,
    Lt,
    Lte,
    Matches,
    Ok,
    Optional,
    Predicate,
    Required,
    V,
    to_pydantic,
    to_validator,
    validate,
)


class TestV:
    def test_simple_check(self):
        is_positive = V(check=lambda x: x > 0)
        assert isinstance(is_positive(5), Ok)
        assert isinstance(is_positive(-1), Err)

    def test_required(self):
        req = V(check=lambda _: True, required=True)
        assert isinstance(req(None), Err)
        assert isinstance(req("value"), Ok)

    def test_optional_none(self):
        opt = V(check=lambda x: isinstance(x, str), required=False)
        assert isinstance(opt(None), Ok)
        assert isinstance(opt("hello"), Ok)

    def test_and_combination(self):
        is_str_nonempty = IsType(str) & V(check=lambda x: len(x) > 0)
        assert isinstance(is_str_nonempty("hello"), Ok)
        assert isinstance(is_str_nonempty(""), Err)
        assert isinstance(is_str_nonempty(123), Err)

    def test_or_combination(self):
        str_or_int = IsType(str) | IsType(int)
        assert isinstance(str_or_int("hello"), Ok)
        assert isinstance(str_or_int(42), Ok)
        assert isinstance(str_or_int(3.14), Err)

    def test_type_as_validator(self):
        combined = str & Required()
        assert isinstance(combined("hello"), Ok)
        assert isinstance(combined(None), Err)

    def test_with_message(self):
        v = V(check=lambda x: x > 0).with_message("Must be positive")
        result = v(-1)
        assert isinstance(result, Err)
        assert result.error[1] == "Must be positive"


class TestValidators:
    def test_required(self):
        v = Required(str)
        assert isinstance(v("hello"), Ok)
        assert isinstance(v(None), Err)

    def test_required_bare(self):
        v = Required()
        assert isinstance(v("anything"), Ok)
        assert isinstance(v(None), Err)

    def test_optional(self):
        v = Optional(str)
        assert isinstance(v(None), Ok)
        assert isinstance(v("hello"), Ok)
        assert isinstance(v(123), Err)

    def test_istype(self):
        v = IsType(int)
        assert isinstance(v(42), Ok)
        assert isinstance(v("42"), Err)

    def test_inrange(self):
        v = InRange(1, 5)
        assert isinstance(v([1, 2, 3]), Ok)
        assert isinstance(v([]), Err)
        assert isinstance(v([1, 2, 3, 4, 5, 6]), Err)

    def test_inset(self):
        v = InSet({"a", "b", "c"})
        assert isinstance(v("a"), Ok)
        assert isinstance(v("d"), Err)

    def test_matches(self):
        v = Matches(r"^[a-z]+$")
        assert isinstance(v("hello"), Ok)
        assert isinstance(v("Hello"), Err)
        assert isinstance(v(123), Err)

    def test_predicate(self):
        v = Predicate(lambda x: x > 0, "Must be positive")
        assert isinstance(v(5), Ok)
        assert isinstance(v(-5), Err)

    def test_gt_gte_lt_lte(self):
        assert isinstance(Gt(5)(6), Ok)
        assert isinstance(Gt(5)(5), Err)
        assert isinstance(Gte(5)(5), Ok)
        assert isinstance(Lt(5)(4), Ok)
        assert isinstance(Lt(5)(5), Err)
        assert isinstance(Lte(5)(5), Ok)

    def test_between(self):
        v = Between(0, 10)
        assert isinstance(v(5), Ok)
        assert isinstance(v(0), Ok)
        assert isinstance(v(10), Ok)
        assert isinstance(v(-1), Err)
        assert isinstance(v(11), Err)

    def test_between_exclusive(self):
        v = Between(0, 10, inclusive=False)
        assert isinstance(v(5), Ok)
        assert isinstance(v(0), Err)
        assert isinstance(v(10), Err)


class TestValidate:
    def test_simple_schema(self):
        schema = {"name": str, "age": int}
        assert isinstance(validate({"name": "Alice", "age": 30}, schema), Ok)
        result = validate({"name": 123, "age": 30}, schema)
        assert isinstance(result, Err)

    def test_nested_schema(self):
        schema = {
            "user": {
                "name": Required(str),
                "email": Optional(str),
            }
        }
        valid = {"user": {"name": "Alice"}}
        invalid = {"user": {"email": "a@b.com"}}  # Missing required name

        assert isinstance(validate(valid, schema), Ok)
        assert isinstance(validate(invalid, schema), Err)

    def test_list_schema(self):
        schema = {"tags": [str]}
        assert isinstance(validate({"tags": ["a", "b"]}, schema), Ok)
        assert isinstance(validate({"tags": ["a", 1]}, schema), Err)

    def test_error_paths(self):
        schema = {"user": {"name": Required(str)}}
        result = validate({"user": {"name": None}}, schema)
        assert isinstance(result, Err)
        errors = result.error
        assert len(errors) == 1
        path, _ = errors[0]
        assert path == ("user", "name")


class TestToPydantic:
    def test_simple_model(self):
        schema = {
            "name": Required(str),
            "age": int,
        }
        User = to_pydantic("User", schema)
        user = User(name="Alice", age=30)
        assert user.name == "Alice"
        assert user.age == 30

    def test_optional_fields(self):
        schema = {
            "name": Required(str),
            "email": Optional(str),
        }
        User = to_pydantic("User", schema)
        user = User(name="Alice")
        assert user.name == "Alice"
        assert user.email is None

    def test_pydantic_validation(self):
        from pydantic import ValidationError

        schema = {"name": Required(str)}
        User = to_pydantic("User", schema)

        with pytest.raises(ValidationError):
            User()  # Missing required field


class TestToValidator:
    def test_type_coercion(self):
        v = to_validator(str)
        assert isinstance(v, V)
        assert isinstance(v("hello"), Ok)

    def test_dict_coercion(self):
        v = to_validator({"name": str})
        assert isinstance(v, DictV)

    def test_list_coercion(self):
        v = to_validator([str])
        assert isinstance(v, ListV)

    def test_callable_coercion(self):
        v = to_validator(lambda x: x > 0)
        assert isinstance(v, V)
        assert isinstance(v(5), Ok)
