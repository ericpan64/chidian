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

from typing import Optional, Union


class LexiconBuilder:
    """Builder for creating Lexicon instances."""

    def __init__(self) -> None:
        self._mappings: dict[str, str] = {}
        self._reverse_priorities: dict[str, str] = {}
        self._default: Optional[str] = None
        self._metadata: dict[str, str] = {}

    def add(self, key: str, value: str) -> "LexiconBuilder":
        """Add a single key-value mapping."""
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("Keys and values must be strings")

        self._mappings[key] = value
        if value not in self._reverse_priorities:
            self._reverse_priorities[value] = key
        return self

    def add_many(self, keys: list[str], value: str) -> "LexiconBuilder":
        """Add multiple keys that map to the same value."""
        if not isinstance(value, str):
            raise TypeError("Value must be a string")

        for i, key in enumerate(keys):
            if not isinstance(key, str):
                raise TypeError("All keys must be strings")
            self._mappings[key] = value
            # First key is default for reverse
            if i == 0 and value not in self._reverse_priorities:
                self._reverse_priorities[value] = key
        return self

    def set_primary_reverse(self, value: str, primary_key: str) -> "LexiconBuilder":
        """Override which key is returned for reverse lookup of a value."""
        if primary_key not in self._mappings or self._mappings[primary_key] != value:
            raise ValueError(f"Key '{primary_key}' must map to value '{value}'")
        self._reverse_priorities[value] = primary_key
        return self

    def set_default(self, default: str) -> "LexiconBuilder":
        """Set default value for missing keys."""
        if not isinstance(default, str):
            raise TypeError("Default must be a string")
        self._default = default
        return self

    def set_metadata(self, metadata: dict[str, str]) -> "LexiconBuilder":
        """Set metadata for the lexicon."""
        self._metadata = metadata
        return self

    def build(self) -> "Lexicon":
        """Build and return the Lexicon instance."""
        lexicon = Lexicon.__new__(Lexicon)
        super(Lexicon, lexicon).__init__(self._mappings)
        lexicon._default = self._default
        lexicon._reverse = self._reverse_priorities.copy()
        lexicon.metadata = self._metadata

        return lexicon


class Lexicon(dict):
    def __init__(
        self,
        mappings: dict[Union[str, tuple], str],
        default: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize a bidirectional string mapper.

        Args:
            mappings: Dict of mappings. Keys can be strings or tuples (for many-to-one).
            default: Default value to return for missing keys
            metadata: Optional metadata about the mapping (version, source, etc.)
        """
        # Process mappings to flatten tuples
        flat_mappings = {}
        reverse_priorities = {}

        for key, value in mappings.items():
            # Validate value type
            if not isinstance(value, str):
                raise TypeError("Values must be strings")

            if isinstance(key, tuple):
                # Many-to-one mapping
                if len(key) == 0:
                    raise ValueError("Empty tuple keys are not allowed")

                for i, k in enumerate(key):
                    if not isinstance(k, str):
                        raise TypeError("All keys in tuples must be strings")
                    flat_mappings[k] = value
                    # First element is default for reverse
                    if i == 0 and value not in reverse_priorities:
                        reverse_priorities[value] = k
            else:
                # One-to-one mapping
                if not isinstance(key, str):
                    raise TypeError("Keys must be strings or tuples of strings")
                flat_mappings[key] = value
                if value not in reverse_priorities:
                    reverse_priorities[value] = key

        # Initialize dict with flat mappings
        super().__init__(flat_mappings)
        self._default = default
        self._reverse = reverse_priorities
        self.metadata = metadata or {}

    def __getitem__(self, key: str) -> str:
        """
        Bidirectional lookup with dict syntax.
        Scans keys first, then values.
        """
        # Try forward lookup first (check in dict keys)
        if super().__contains__(key):
            return super().__getitem__(key)

        # Try reverse lookup
        # First check if it's in our reverse priority mapping
        if key in self._reverse:
            return self._reverse[key]

        # If not in priority mapping, search all values
        for k, v in self.items():
            if v == key:
                return k

        # Check if we have a default value
        if self._default is not None:
            return self._default

        # Raise KeyError if not found and no default
        raise KeyError(f"Key '{key}' not found")

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:  # type: ignore[override]
        """
        Safe bidirectional lookup with default.
        Scans keys first, then values.
        """
        # Try forward lookup first (check in dict keys)
        if super().__contains__(key):
            return super().__getitem__(key)

        # Try reverse lookup
        # First check if it's in our reverse priority mapping
        if key in self._reverse:
            return self._reverse[key]

        # If not in priority mapping, search all values
        for k, v in self.items():
            if v == key:
                return k

        # Key doesn't exist, use provided default if given, otherwise instance default
        return default if default is not None else self._default

    def __contains__(self, key: object) -> bool:
        """Check if key exists in either forward or reverse mapping."""
        if isinstance(key, str):
            return super().__contains__(key) or key in self._reverse
        return False

    def forward(self, key: str) -> Optional[str]:
        """Transform from source to target format."""
        return super().get(key)

    def reverse(self, key: str) -> Optional[str]:
        """Transform from target back to source format."""
        return self._reverse.get(key)

    def can_reverse(self) -> bool:
        """Lexicon always supports reverse transformation."""
        return True

    @classmethod
    def builder(cls) -> LexiconBuilder:
        """Create a new LexiconBuilder instance."""
        return LexiconBuilder()
