"""
Core validator classes for chidian validation.

Provides V, DictV, ListV dataclasses with functional composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .types import CheckFn, Err, Ok, Path


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

    def __call__(self, value: Any, path: Path = ()) -> Ok[Any] | Err[tuple[Path, str]]:
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

    def __and__(self, other: V | type | Callable | dict | list) -> V:
        """Combine with AND logic: both must pass."""
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine V with nested structure using &")

        def combined_check(x: Any) -> bool:
            return self.check(x) and other_v.check(x)

        return V(
            check=combined_check,
            required=self.required or other_v.required,
            type_hint=self.type_hint or other_v.type_hint,
            message=self.message or other_v.message,
        )

    def __rand__(self, other: type | Callable | dict | list) -> V:
        """Support `str & Required()` where str comes first."""
        return to_validator(other) & self

    def __or__(self, other: V | type | Callable) -> V:
        """Combine with OR logic: at least one must pass."""
        other_v = to_validator(other)
        if not isinstance(other_v, V):
            raise TypeError("Cannot combine V with nested structure using |")

        def combined_check(x: Any) -> bool:
            return self.check(x) or other_v.check(x)

        return V(
            check=combined_check,
            required=self.required and other_v.required,
            type_hint=None,  # Union type - defer to Pydantic
        )

    def __ror__(self, other: type | Callable) -> V:
        """Support `str | int` where str comes first."""
        return to_validator(other) | self

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

    def __call__(
        self, value: Any, path: Path = ()
    ) -> Ok[Any] | Err[list[tuple[Path, str]]]:
        if value is None:
            if self.required:
                return Err([(path, "Required dict is missing")])
            return Ok(None)

        if not isinstance(value, dict):
            return Err([(path, f"Expected dict, got {type(value).__name__}")])

        errors: list[tuple[Path, str]] = []

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

    def __call__(
        self, value: Any, path: Path = ()
    ) -> Ok[Any] | Err[list[tuple[Path, str]]]:
        if value is None:
            if self.required:
                return Err([(path, "Required list is missing")])
            return Ok(None)

        if not isinstance(value, list):
            return Err([(path, f"Expected list, got {type(value).__name__}")])

        errors: list[tuple[Path, str]] = []

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
        type -> V(check=isinstance, type_hint=type)
        dict -> DictV with recursive conversion
        list -> ListV with item validator from list[0]
        Callable -> V(check=callable)
    """
    match v:
        case V() | DictV() | ListV():
            return v
        case type():

            def type_check(x: Any, t: type = v) -> bool:
                return isinstance(x, t)

            return V(check=type_check, type_hint=v)
        case dict():
            fields = {k: to_validator(val) for k, val in v.items()}
            return DictV(fields=fields)
        case list() if len(v) == 1:
            return ListV(items=to_validator(v[0]))
        case list() if len(v) > 1:
            # Multiple items = OR logic for item types (must be V instances)
            item_v: V = to_validator(v[0])  # type: ignore[assignment]
            for other in v[1:]:
                other_v = to_validator(other)
                if isinstance(item_v, V) and isinstance(other_v, V):
                    item_v = item_v | other_v
            return ListV(items=item_v)
        case _ if callable(v):
            return V(check=v)

    raise TypeError(f"Cannot convert {type(v).__name__} to validator")
