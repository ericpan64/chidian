"""
Bidirectional string mapper for code/terminology translations.

Primary use case: Medical code system mappings (e.g., LOINC ↔ SNOMED).
Supports both one-to-one and many-to-one relationships with automatic
reverse lookup generation.

Examples:
    Simple code mapping:
    >>> loinc_to_snomed = Lexicon({'8480-6': '271649006'})
    >>> loinc_to_snomed['8480-6']  # Forward lookup
    '271649006'
    >>> loinc_to_snomed['271649006']  # Reverse lookup
    '8480-6'

    Many-to-one mapping (first value is default):
    >>> mapper = Lexicon({('LA6699-8', 'LA6700-4'): 'absent'})
    >>> mapper['absent']  # Returns first key as default
    'LA6699-8'
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from typing import Optional


class Lexicon(Mapping[str, str]):
    """
    Bidirectional string mapper for code/terminology translations.

    - Many->one supported by allowing tuple/list of keys.
    - Reverse lookup returns the first key seen for a given value.
    - Default (if set) is returned when a key/value isn't found instead of KeyError.
    """

    def __init__(
        self,
        mappings: Mapping[str | Sequence[str], str],
        default: Optional[str] = None,
        metadata: Optional[Mapping[str, str]] = None,
    ) -> None:
        fwd: dict[str, str] = {}
        rev: dict[str, str] = {}

        for key, value in mappings.items():
            if not isinstance(value, str):
                raise TypeError("Values must be strings")

            if isinstance(key, str):
                fwd[key] = value
                if value not in rev:
                    rev[value] = key
                continue

            if isinstance(key, Sequence) and not isinstance(key, str):
                if len(key) == 0:
                    raise ValueError("Empty tuple keys are not allowed")
                for i, k in enumerate(key):
                    if not isinstance(k, str):
                        raise TypeError("All keys in tuples must be strings")
                    fwd[k] = value
                    if i == 0 and value not in rev:
                        rev[value] = k
                continue

            raise TypeError("Keys must be strings or tuples of strings")

        self._fwd = fwd
        self._rev = rev
        self._default = default
        self.metadata: dict[str, str] = dict(metadata or {})

    # Mapping interface
    def __len__(self) -> int:
        return len(self._fwd)

    def __iter__(self) -> Iterator[str]:
        return iter(self._fwd)

    def __getitem__(self, key: str) -> str:
        if key in self._fwd:
            return self._fwd[key]
        if key in self._rev:
            return self._rev[key]
        if self._default is not None:
            return self._default
        raise KeyError(f"Key '{key}' not found")

    # Dict-like conveniences with bidirectional semantics
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:  # type: ignore[override]
        if key in self._fwd:
            return self._fwd[key]
        if key in self._rev:
            return self._rev[key]
        return default if default is not None else self._default

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and (key in self._fwd or key in self._rev)

    # Explicit helpers
    def forward(self, key: str) -> Optional[str]:
        return self._fwd.get(key)

    def reverse(self, value: str) -> Optional[str]:
        return self._rev.get(value)

    def prefer(self, value: str, primary_key: str) -> None:
        """Override which key is returned for reverse lookup of a value."""
        if self._fwd.get(primary_key) != value:
            raise ValueError(f"Key '{primary_key}' must map to value '{value}'")
        self._rev[value] = primary_key

    @classmethod
    def builder(cls) -> LexiconBuilder:
        return LexiconBuilder()


class LexiconBuilder:
    """Fluent builder for creating Lexicon instances."""

    def __init__(self) -> None:
        self._mappings: dict[str, str] = {}
        self._reverse_priorities: dict[str, str] = {}
        self._default: Optional[str] = None
        self._metadata: dict[str, str] = {}

    def add(self, key: str, value: str) -> LexiconBuilder:
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("Keys and values must be strings")
        self._mappings[key] = value
        if value not in self._reverse_priorities:
            self._reverse_priorities[value] = key
        return self

    def add_many(self, keys: Sequence[str], value: str) -> LexiconBuilder:
        if not isinstance(value, str):
            raise TypeError("Value must be a string")
        if len(keys) == 0:
            raise ValueError("Empty tuple keys are not allowed")
        for i, key in enumerate(keys):
            if not isinstance(key, str):
                raise TypeError("All keys must be strings")
            self._mappings[key] = value
            if i == 0 and value not in self._reverse_priorities:
                self._reverse_priorities[value] = key
        return self

    def set_primary_reverse(self, value: str, primary_key: str) -> LexiconBuilder:
        if self._mappings.get(primary_key) != value:
            raise ValueError(f"Key '{primary_key}' must map to value '{value}'")
        self._reverse_priorities[value] = primary_key
        return self

    def set_default(self, default: str) -> LexiconBuilder:
        if not isinstance(default, str):
            raise TypeError("Default must be a string")
        self._default = default
        return self

    def set_metadata(self, metadata: Mapping[str, str]) -> LexiconBuilder:
        self._metadata = dict(metadata)
        return self

    def build(self) -> Lexicon:
        lex = Lexicon(self._mappings, default=self._default, metadata=self._metadata)  # type: ignore
        for value, primary in self._reverse_priorities.items():
            lex.prefer(value, primary)
        return lex
