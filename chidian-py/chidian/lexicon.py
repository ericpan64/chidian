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

from chidian_rs import LexiconCore  # type: ignore[attr-defined]


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

        # Initialize Rust core for high-performance lookups
        lexicon._core = LexiconCore(
            self._mappings, self._reverse_priorities, self._default
        )

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

        # Initialize Rust core for high-performance lookups
        self._core = LexiconCore(flat_mappings, reverse_priorities, default)

    def __getitem__(self, key: str) -> str:
        """
        Bidirectional lookup with dict syntax.
        Scans keys first, then values.
        """
        # Use Rust core for better performance
        return self._core.get_bidirectional_strict(key)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:  # type: ignore[override]
        """
        Safe bidirectional lookup with default.
        Scans keys first, then values.
        """
        # Check if key exists first - if it does, get the value
        if self._core.contains_bidirectional(key):
            # Key exists, so we can safely get the value
            # We know this won't be None since the key exists
            return self._core.get_bidirectional(key)

        # Key doesn't exist, use provided default if given, otherwise instance default
        return default if default is not None else self._default

    def __contains__(self, key: object) -> bool:
        """Check if key exists in either forward or reverse mapping."""
        # Use Rust core for better performance
        if isinstance(key, str):
            return self._core.contains_bidirectional(key)
        return False

    def forward(self, key: str) -> Optional[str]:
        """Transform from source to target format."""
        # Use Rust core for better performance
        return self._core.forward_only(key)

    def reverse(self, key: str) -> Optional[str]:
        """Transform from target back to source format."""
        # Use Rust core for better performance
        return self._core.reverse_only(key)

    def can_reverse(self) -> bool:
        """Lexicon always supports reverse transformation."""
        return True

    @classmethod
    def builder(cls) -> LexiconBuilder:
        """Create a new LexiconBuilder instance."""
        return LexiconBuilder()
