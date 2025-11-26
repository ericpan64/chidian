"""
Built-in validators for chidian validation.

Provides factory functions that return V instances.
"""

from __future__ import annotations

import re
from typing import Any

from .core import V, to_validator


def Required(v: V | type | None = None) -> V:
    """
    Mark a field as required (cannot be None).

    Usage:
        Required()           # Just required, no type check
        Required(str)        # Required string
        str & Required()     # Same as above
    """
    if v is None:
        return V(check=lambda _: True, required=True)

    inner = to_validator(v)
    if not isinstance(inner, V):
        raise TypeError(
            "Required() on nested structures: use the nested validator directly"
        )

    return V(
        check=inner.check,
        required=True,
        type_hint=inner.type_hint,
        message=inner.message,
    )


def Optional(v: V | type) -> V:
    """
    Allow None, validate if present.

    Usage:
        Optional(str)        # None or valid string
    """
    inner = to_validator(v)
    if not isinstance(inner, V):
        raise TypeError("Optional() requires a simple validator, not nested structure")

    def check(x: Any) -> bool:
        return x is None or inner.check(x)

    return V(
        check=check,
        required=False,
        type_hint=inner.type_hint,
    )


def IsType(t: type) -> V:
    """
    Validate that value is an instance of type.

    Usage:
        IsType(str)
        IsType(int) & InRange(0, 100)
    """

    def check(x: Any) -> bool:
        return isinstance(x, t)

    return V(
        check=check,
        type_hint=t,
        message=f"Expected {t.__name__}",
    )


def InRange(lower: int | None = None, upper: int | None = None) -> V:
    """
    Validate length is within range (inclusive).

    Usage:
        InRange(1, 10)      # 1 to 10 items
        InRange(lower=5)    # At least 5
        InRange(upper=20)   # At most 20
    """

    def check(x: Any) -> bool:
        try:
            n = len(x)
        except TypeError:
            return False
        if lower is not None and n < lower:
            return False
        if upper is not None and n > upper:
            return False
        return True

    msg_parts = []
    if lower is not None:
        msg_parts.append(f">= {lower}")
    if upper is not None:
        msg_parts.append(f"<= {upper}")
    msg = f"Length must be {' and '.join(msg_parts)}"

    return V(check=check, message=msg)


def MinLength(n: int) -> V:
    """Validate minimum length."""
    return InRange(lower=n)


def MaxLength(n: int) -> V:
    """Validate maximum length."""
    return InRange(upper=n)


def InSet(values: set | frozenset | list | tuple) -> V:
    """
    Validate value is in a set of allowed values.

    Usage:
        InSet({"active", "inactive", "pending"})
        InSet([1, 2, 3])
    """
    container = frozenset(values)

    def check(x: Any) -> bool:
        return x in container

    return V(
        check=check,
        message=f"Must be one of: {container}",
    )


def Matches(pattern: str) -> V:
    """
    Validate string matches regex pattern.

    Usage:
        Matches(r"^[a-z]+$")
        Matches(r"\\d{3}-\\d{4}")
    """
    compiled = re.compile(pattern)

    def check(x: Any) -> bool:
        return isinstance(x, str) and compiled.match(x) is not None

    return V(
        check=check,
        type_hint=str,
        message=f"Must match pattern: {pattern}",
    )


def Predicate(fn: Any, message: str | None = None) -> V:
    """
    Create validator from arbitrary predicate function.

    Usage:
        Predicate(lambda x: x > 0, "Must be positive")
        Predicate(str.isalpha, "Must be alphabetic")
    """
    return V(check=fn, message=message)


def Eq(value: Any) -> V:
    """Validate exact equality."""

    def check(x: Any) -> bool:
        return x == value

    return V(check=check, message=f"Must equal {repr(value)}")


def Gt(value: Any) -> V:
    """Validate greater than."""

    def check(x: Any) -> bool:
        return x > value

    return V(check=check, message=f"Must be > {value}")


def Gte(value: Any) -> V:
    """Validate greater than or equal."""

    def check(x: Any) -> bool:
        return x >= value

    return V(check=check, message=f"Must be >= {value}")


def Lt(value: Any) -> V:
    """Validate less than."""

    def check(x: Any) -> bool:
        return x < value

    return V(check=check, message=f"Must be < {value}")


def Lte(value: Any) -> V:
    """Validate less than or equal."""

    def check(x: Any) -> bool:
        return x <= value

    return V(check=check, message=f"Must be <= {value}")


def Between(lower: Any, upper: Any, inclusive: bool = True) -> V:
    """Validate value is between bounds."""
    if inclusive:

        def check(x: Any) -> bool:
            return lower <= x <= upper

        return V(
            check=check,
            message=f"Must be between {lower} and {upper}",
        )

    def check_exclusive(x: Any) -> bool:
        return lower < x < upper

    return V(
        check=check_exclusive,
        message=f"Must be between {lower} and {upper} (exclusive)",
    )
