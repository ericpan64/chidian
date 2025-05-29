from typing import Any, Optional

"""
Base class for data transformation between different representations.

A Mapper defines how to convert data from one format to another, supporting
use cases like healthcare data interoperability (FHIR ↔ OMOP).
"""
# Make this a Python protocol
class Mapper(dict):
    ...

"""
Bidirectional string mapper for code/terminology translations.

Primary use case: Medical code system mappings (e.g., LOINC ↔ SNOMED).
Supports both one-to-one and many-to-one relationships with automatic
reverse lookup generation.

Examples:
    Simple code mapping:
    >>> loinc_to_snomed = StringMapper({'8480-6': '271649006'})
    >>> loinc_to_snomed['8480-6']  # Forward lookup
    '271649006'
    >>> loinc_to_snomed['271649006']  # Reverse lookup
    '8480-6'
    
    Many-to-one mapping (first value is default):
    >>> mapper = StringMapper({('LA6699-8', 'LA6700-4'): 'absent'})
    >>> mapper['absent']  # Returns first key as default
    'LA6699-8'
"""
class StringMapper(Mapper):
    def __init__(self, mappings: dict, default: Any = None, metadata: Optional[dict] = None):
        """
        Initialize a bidirectional string mapper.
        
        Args:
            mappings: Dict of string mappings. Keys can be strings or tuples (for many-to-one).
            default: Default value to return for missing keys
            metadata: Optional metadata about the mapping (version, source, etc.)
        """
        super().__init__()
        self._forward = {}
        self._reverse = {}
        self._default = default
        self.metadata = metadata or {}
        
        # Build forward and reverse mappings
        for key, value in mappings.items():
            if isinstance(key, tuple):
                # Many-to-one mapping
                for k in key:
                    self._forward[k] = value
                # First element is default for reverse
                if value not in self._reverse:
                    self._reverse[value] = key[0]
            else:
                # One-to-one mapping
                self._forward[key] = value
                if value not in self._reverse:
                    self._reverse[value] = key
        
        # Store in parent dict for dict-like access
        self.update(self._forward)
    
    def forward(self, key: str) -> Optional[str]:
        """Transform from source to target format."""
        return self._forward.get(key, self._default)
    
    def reverse(self, key: str) -> Optional[str]:
        """Transform from target back to source format."""
        return self._reverse.get(key, self._default)
    
    def __getitem__(self, key: str) -> str:
        """Support bidirectional lookup with dict syntax."""
        # Try forward first, then reverse
        if key in self._forward:
            return self._forward[key]
        elif key in self._reverse:
            return self._reverse[key]
        else:
            if self._default is not None:
                return self._default
            raise KeyError(f"Key '{key}' not found in forward or reverse mappings")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Safe bidirectional lookup with default."""
        if key in self._forward:
            return self._forward[key]
        elif key in self._reverse:
            return self._reverse[key]
        else:
            # Use provided default if given, otherwise instance default
            return default if default is not None else self._default
    
    def __contains__(self, key: str) -> bool:
        """Check if key exists in either direction."""
        return key in self._forward or key in self._reverse
    
    def __len__(self) -> int:
        """Return total number of unique mappings."""
        return len(self._forward) + len(self._reverse)
    
    def can_reverse(self) -> bool:
        """StringMapper always supports reverse transformation."""
        return True
    
    def get_conflicts(self) -> dict[str, list[str]]:
        """Return any reverse mapping conflicts (multiple sources → same target)."""
        conflicts = {}
        reverse_counts = {}
        
        for key, value in self._forward.items():
            if value not in reverse_counts:
                reverse_counts[value] = []
            reverse_counts[value].append(key)
        
        for value, keys in reverse_counts.items():
            if len(keys) > 1:
                conflicts[value] = keys
        
        return conflicts

"""
Flexible structure mapper for complex data transformations.

Handles all non-string mappings including:
- Nested ↔ flat conversions (FHIR resources ↔ OMOP tables)
- Conditional field inclusion/exclusion
- Array flattening and restructuring
- Complex field transformations with custom logic

Integrates with seeds (DROP, KEEP, ELIF) for fine-grained control over
which fields to include based on data conditions.

Example:
    >>> fhir_to_omop = StructMapper({
    ...     'person_id': 'subject.reference',
    ...     'value': {
    ...         'source': 'valueQuantity.value',
    ...         'condition': lambda o: 'valueQuantity' in o
    ...     }
    ... })
"""
class StructMapper(Mapper):

    ...

# """
# A `BijectiveStructMapper` is a `StructMapper` that is bijective, i.e. it has a one-to-one mapping in both directions
# """
# class BijectiveStructMapper(StructMapper):

#     # Defines a `put` method and save state for reverse lookup
#     def put(...) -> ...:
#         ...
#     ...