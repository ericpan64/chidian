"""
Chidian Validation - Dict-like schema validation with Pydantic interop.

Usage:
    from chidian.validation import V, Required, Optional, validate, to_pydantic

    schema = {
        "name": Required(str),
        "email": Optional(str),
        "tags": [str],
    }

    result = validate(data, schema)
    Model = to_pydantic("MyModel", schema)
"""

from .core import DictV, ListV, V, to_validator
from .schema import to_pydantic, validate
from .types import Err, Ok
from .validators import (
    Between,
    Eq,
    Gt,
    Gte,
    InRange,
    InSet,
    IsType,
    Lt,
    Lte,
    Matches,
    MaxLength,
    MinLength,
    Optional,
    Predicate,
    Required,
)

__all__ = [
    # Result types
    "Ok",
    "Err",
    # Core
    "V",
    "DictV",
    "ListV",
    "to_validator",
    # Validators
    "Required",
    "Optional",
    "IsType",
    "InRange",
    "MinLength",
    "MaxLength",
    "InSet",
    "Matches",
    "Predicate",
    "Eq",
    "Gt",
    "Gte",
    "Lt",
    "Lte",
    "Between",
    # Schema
    "validate",
    "to_pydantic",
]
