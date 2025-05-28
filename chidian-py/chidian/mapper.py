from typing import Any

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
    def __call__(self, key: str | tuple) -> str | tuple:
        ...

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