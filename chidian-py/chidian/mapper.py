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
    def __init__(
        self,
        source_model: type,  # Required Pydantic BaseModel
        target_model: type,  # Required Pydantic BaseModel
        mapping: dict[str, Any],
        strict: bool = True,  # Default to strict when models are provided
        metadata: Optional[dict] = None
    ):
        """
        Initialize a type-safe structure mapper between Pydantic models.
        
        Args:
            source_model: Source Pydantic BaseModel class
            target_model: Target Pydantic BaseModel class
            mapping: Field mapping definitions
            strict: If True, validate against models and fail on errors (default True)
            metadata: Optional metadata about the mapping
        """
        super().__init__()
        
        # Validate that models are Pydantic BaseModels
        if not (hasattr(source_model, 'model_fields') or hasattr(source_model, '__fields__')):
            raise TypeError(f"source_model must be a Pydantic BaseModel, got {type(source_model)}")
        if not (hasattr(target_model, 'model_fields') or hasattr(target_model, '__fields__')):
            raise TypeError(f"target_model must be a Pydantic BaseModel, got {type(target_model)}")
        
        self.source_model = source_model
        self.target_model = target_model
        self.mapping = mapping
        self.strict = strict
        self.metadata = metadata or {}
        
        # Validate mapping at initialization
        validation_issues = self.validate_mapping()
        if self.strict and validation_issues['missing_required_fields']:
            raise ValueError(
                f"Missing required target fields in mapping: {validation_issues['missing_required_fields']}"
            )
        
        # Import here to avoid circular imports
        from .chidian import get as _get
        from .partials import FunctionChain, ChainableFn
        self._get = _get
        self._function_chain = FunctionChain
        self._chainable_fn = ChainableFn
    
    def forward(self, source: 'BaseModel') -> 'BaseModel':
        """
        Transform source model to target model.
        
        Args:
            source: Instance of source_model
            
        Returns:
            Instance of target_model
        """
        # Validate input type
        if not isinstance(source, self.source_model):
            if self.strict:
                raise TypeError(f"Expected {self.source_model.__name__}, got {type(source).__name__}")
            # Try to convert if not strict
            if hasattr(self.source_model, 'model_validate'):
                source = self.source_model.model_validate(source)
            else:
                source = self.source_model(**source)
        
        # Convert to dict for processing
        if hasattr(source, 'model_dump'):
            source_dict = source.model_dump()
        elif hasattr(source, 'dict'):
            source_dict = source.dict()
        else:
            source_dict = source
        
        result = {}
        
        for target_field, mapping_spec in self.mapping.items():
            try:
                value = self._process_mapping(source_dict, mapping_spec)
                
                # Skip None values unless we're being strict
                if value is not None or self.strict:
                    result[target_field] = value
                    
            except Exception as e:
                if self.strict:
                    raise ValueError(f"Error mapping field '{target_field}': {e}")
                # In non-strict mode, skip failed mappings
                continue
        
        # Validate and construct target model
        try:
            # Handle Pydantic BaseModel
            if hasattr(self.target_model, 'model_validate'):
                return self.target_model.model_validate(result)
            elif hasattr(self.target_model, 'parse_obj'):
                return self.target_model.parse_obj(result)
            else:
                return self.target_model(**result)
        except Exception as e:
            if self.strict:
                raise ValueError(f"Failed to construct {self.target_model.__name__}: {e}")
            # Return dict as fallback
            return result
    
    def _process_mapping(self, source: dict, mapping_spec: Any) -> Any:
        """Process a single mapping specification."""
        # String path - use get
        if isinstance(mapping_spec, str):
            return self._get(source, mapping_spec)
        
        # FunctionChain or ChainableFn
        elif hasattr(mapping_spec, '__call__'):
            # Check if it's a chainable function or chain
            if hasattr(mapping_spec, 'operations') or hasattr(mapping_spec, 'func'):
                return mapping_spec(source)
            # Regular callable
            else:
                return mapping_spec(source)
        
        # Dict with conditional logic (legacy support)
        elif isinstance(mapping_spec, dict):
            if 'source' in mapping_spec:
                # Check condition if present
                if 'condition' in mapping_spec:
                    if not mapping_spec['condition'](source):
                        return None
                
                # Get the value
                value = self._process_mapping(source, mapping_spec['source'])
                
                # Apply transform if present
                if 'transform' in mapping_spec:
                    value = mapping_spec['transform'](value)
                
                return value
            else:
                # Nested mapping
                return {k: self._process_mapping(source, v) for k, v in mapping_spec.items()}
        
        # SEED objects (they should have an evaluate method)
        elif hasattr(mapping_spec, 'evaluate'):
            return mapping_spec.evaluate(source)
        
        # Direct value
        else:
            return mapping_spec
    
    def reverse(self, target: Any) -> Any:
        """
        Reverse transformation (target to source).
        
        Note: This is only possible for simple mappings. Complex transformations
        with functions or conditions are generally not reversible.
        """
        raise NotImplementedError(
            "StructMapper reverse transformation is not implemented. "
            "For reversible mappings, consider using BijectiveStructMapper (future feature)."
        )
    
    def can_reverse(self) -> bool:
        """StructMapper generally cannot reverse complex transformations."""
        return False
    
    def validate_mapping(self) -> dict[str, list[str]]:
        """
        Validate the mapping against source and target models.
        
        Returns:
            Dict of validation issues by category
        """
        issues = {
            'missing_required_fields': [],
            'unknown_target_fields': [],
            'invalid_source_fields': []
        }
        
        # Get target model fields
        target_fields = self._get_model_fields(self.target_model)
        source_fields = self._get_model_fields(self.source_model)
        
        # Check for required fields
        required_fields = {
            name for name, field_info in target_fields.items()
            if self._is_field_required(field_info)
        }
        mapped_fields = set(self.mapping.keys())
        issues['missing_required_fields'] = list(required_fields - mapped_fields)
        
        # Check for unknown target fields
        all_target_fields = set(target_fields.keys())
        issues['unknown_target_fields'] = list(mapped_fields - all_target_fields)
        
        # TODO: Validate source paths exist in source model
        
        return issues
    
    def _get_model_fields(self, model: type) -> dict:
        """Get fields from Pydantic model (v1 or v2 compatible)."""
        if hasattr(model, 'model_fields'):
            # Pydantic v2
            return model.model_fields
        elif hasattr(model, '__fields__'):
            # Pydantic v1
            return model.__fields__
        else:
            return {}
    
    def _is_field_required(self, field_info) -> bool:
        """Check if field is required (v1/v2 compatible)."""
        if hasattr(field_info, 'is_required'):
            # Pydantic v1
            return field_info.is_required()
        elif hasattr(field_info, 'default'):
            # Pydantic v2 - required if no default
            return field_info.default is ...
        else:
            return False

# """
# A `BijectiveStructMapper` is a `StructMapper` that is bijective, i.e. it has a one-to-one mapping in both directions
# """
# class BijectiveStructMapper(StructMapper):

#     # Defines a `put` method and save state for reverse lookup
#     def put(...) -> ...:
#         ...
#     ...