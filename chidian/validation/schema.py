"""
Schema operations for chidian validation.

Provides validate() and to_pydantic() functions.
"""

from __future__ import annotations

from typing import Any
from typing import Optional as TypingOptional

from pydantic import create_model

from .core import DictV, ListV, V, to_validator
from .types import Err, Ok, Path


def validate(
    data: dict[str, Any], schema: dict[str, Any]
) -> Ok[dict[str, Any]] | Err[list[tuple[Path, str]]]:
    """
    Validate data against a schema.

    Args:
        data: The dict to validate
        schema: Dict-like schema definition

    Returns:
        Ok(data) if validation passes
        Err([(path, message), ...]) if validation fails

    Usage:
        schema = {
            "name": Required(str),
            "email": str,
            "age": int & Gte(0),
        }
        result = validate({"name": "Alice", "age": 30}, schema)
    """
    validator = to_validator(schema)

    if not isinstance(validator, DictV):
        raise TypeError("Schema must be a dict")

    return validator(data)


def to_pydantic(name: str, schema: dict[str, Any]) -> type:
    """
    Compile schema to a Pydantic model.

    Args:
        name: Name of the generated model class
        schema: Dict-like schema definition

    Returns:
        A Pydantic BaseModel subclass

    Usage:
        User = to_pydantic("User", {
            "name": Required(str),
            "email": Optional(str),
        })
        user = User(name="Alice")
    """
    validator = to_validator(schema)
    if not isinstance(validator, DictV):
        raise TypeError("Schema must be a dict")

    fields: dict[str, Any] = {}

    for key, v in validator.fields.items():
        field_type, default = _extract_pydantic_field(v)
        fields[key] = (field_type, default)

    return create_model(name, **fields)


def _extract_pydantic_field(v: V | DictV | ListV) -> tuple[Any, Any]:
    """Extract Pydantic field type and default from validator."""
    match v:
        case V(required=True, type_hint=t):
            return (t or Any, ...)
        case V(required=False, type_hint=t):
            return (TypingOptional[t or Any], None)
        case DictV(required=req):
            if req:
                return (dict[str, Any], ...)
            return (dict[str, Any] | None, None)
        case ListV(required=req, items=items):
            item_type, _ = _extract_pydantic_field(items)
            if req:
                return (list[item_type], ...)  # type: ignore[valid-type]
            return (list[item_type] | None, None)  # type: ignore[valid-type]

    return (Any, None)
