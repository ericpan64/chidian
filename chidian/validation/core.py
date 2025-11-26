"""
Core validator classes for chidian validation.

Provides V, DictV, ListV dataclasses with functional composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import CheckFn, Err, Ok, Path, ValidationError, ValidationErrors


@dataclass(frozen=True, slots=True)
class V:
    """
    Immutable validator node.

    The fundamental building block. Wraps a check function with metadata
    for composition and Pydantic generation.
    """

    check: CheckFn
    required: bool = False
    type_hint: type | None = None
    message: str | None = None

    def __call__(self, value: Any, path: Path = ()) -> Ok[Any] | Err[ValidationError]:
        """
        Validate a value.

        Returns:
            Ok(value) if validation passes
            Err((path, message)) if validation fails
        """
        if value is None:
            if self.required:
                msg = self.message or "Required field is missing"
                return Err((path, msg))
            return Ok(None)

        try:
            passed = self.check(value)
        except Exception as e:
            return Err((path, f"Validation error: {e}"))

        if not passed:
            msg = self.message or f"Validation failed for value: {repr(value)[:50]}"
            return Err((path, msg))

        return Ok(value)

    def __and__(self, other: V | type | Any) -> V:
        """
        Combine with AND logic: both must pass.

        Usage:
            str & Required()
            IsType(int) & InRange(0, 100)
        """
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine V with nested validator using &")

        def combined_check(x: Any) -> bool:
            return self.check(x) and other_v.check(x)

        return V(
            check=combined_check,
            required=self.required or other_v.required,
            type_hint=self.type_hint or other_v.type_hint,
            message=self.message or other_v.message,
        )

    def __rand__(self, other: type | Any) -> V:
        """Support `str & Required()` where str comes first."""
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine type with V using &")
        return other_v & self

    def __or__(self, other: V | type | Any) -> V:
        """
        Combine with OR logic: at least one must pass.

        Usage:
            str | int
            IsType(str) | IsType(int)
        """
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine V with nested validator using |")

        def combined_check(x: Any) -> bool:
            return self.check(x) or other_v.check(x)

        return V(
            check=combined_check,
            required=self.required and other_v.required,
            type_hint=None,  # Union type - defer to Pydantic
        )

    def __ror__(self, other: type | Any) -> V:
        """Support `str | int` where str comes first."""
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine type with V using |")
        return other_v | self

    def with_message(self, msg: str) -> V:
        """Return new validator with custom error message."""
        return V(
            check=self.check,
            required=self.required,
            type_hint=self.type_hint,
            message=msg,
        )


@dataclass(frozen=True, slots=True)
class DictV:
    """Validator for dict structures with nested field validators."""

    fields: dict[str, V | DictV | ListV]
    required: bool = False

    def __call__(self, value: Any, path: Path = ()) -> Ok[Any] | Err[ValidationErrors]:
        if value is None:
            if self.required:
                return Err([(path, "Required dict is missing")])
            return Ok(None)

        if not isinstance(value, dict):
            return Err([(path, f"Expected dict, got {type(value).__name__}")])

        errors: ValidationErrors = []

        for key, validator in self.fields.items():
            field_path = (*path, key)
            field_value = value.get(key)
            result = validator(field_value, field_path)

            if isinstance(result, Err):
                err = result.error
                if isinstance(err, list):
                    errors.extend(err)
                else:
                    errors.append(err)

        return Err(errors) if errors else Ok(value)


@dataclass(frozen=True, slots=True)
class ListV:
    """Validator for list structures with item validation."""

    items: V | DictV | ListV
    min_length: int | None = None
    max_length: int | None = None
    required: bool = False

    def __call__(self, value: Any, path: Path = ()) -> Ok[Any] | Err[ValidationErrors]:
        if value is None:
            if self.required:
                return Err([(path, "Required list is missing")])
            return Ok(None)

        if not isinstance(value, list):
            return Err([(path, f"Expected list, got {type(value).__name__}")])

        errors: ValidationErrors = []

        if self.min_length is not None and len(value) < self.min_length:
            errors.append((path, f"List too short: {len(value)} < {self.min_length}"))
        if self.max_length is not None and len(value) > self.max_length:
            errors.append((path, f"List too long: {len(value)} > {self.max_length}"))

        for i, item in enumerate(value):
            item_path = (*path, i)
            result = self.items(item, item_path)
            if isinstance(result, Err):
                err = result.error
                if isinstance(err, list):
                    errors.extend(err)
                else:
                    errors.append(err)

        return Err(errors) if errors else Ok(value)


def to_validator(v: Any) -> V | DictV | ListV:
    """
    Coerce a value to a validator.

    Conversion rules:
        V | DictV | ListV -> pass through
        type -> V with isinstance check
        dict -> DictV with recursive conversion
        list -> ListV with item validator from list[0]
        Callable -> V(check=callable)
    """
    if isinstance(v, (V, DictV, ListV)):
        return v

    if isinstance(v, type):

        def type_check(x: Any, t: type = v) -> bool:
            return isinstance(x, t)

        return V(check=type_check, type_hint=v)

    if isinstance(v, dict):
        fields = {k: to_validator(val) for k, val in v.items()}
        return DictV(fields=fields)

    if isinstance(v, list):
        if len(v) == 0:
            raise ValueError("Empty list cannot be converted to validator")
        if len(v) == 1:
            return ListV(items=to_validator(v[0]))
        # Multiple items = OR logic for item types (only works with V)
        first = to_validator(v[0])
        if not isinstance(first, V):
            raise TypeError(
                "Multiple list item types only supported for simple validators"
            )
        item_v: V = first
        for other in v[1:]:
            other_v = to_validator(other)
            if not isinstance(other_v, V):
                raise TypeError(
                    "Multiple list item types only supported for simple validators"
                )
            item_v = item_v | other_v
        return ListV(items=item_v)

    if callable(v):
        return V(check=v)

    raise TypeError(f"Cannot convert {type(v).__name__} to validator")
