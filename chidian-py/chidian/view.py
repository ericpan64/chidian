from typing import Any, Optional

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
    >>> fhir_to_omop = View({
    ...     'person_id': 'subject.reference',
    ...     'value': {
    ...         'source': 'valueQuantity.value',
    ...         'condition': lambda o: 'valueQuantity' in o
    ...     }
    ... })
"""
class View:
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
        
        # Validate mapping at initialization if strict
        if self.strict:
            validation_issues = self._validate_mapping()
            if validation_issues['missing_required_fields']:
                raise ValueError(
                    f"Missing required target fields in mapping: {validation_issues['missing_required_fields']}"
                )
        
        # Import here to avoid circular imports
        from .chidian_rs import get as _get
        from .partials import FunctionChain, ChainableFn
        self._get = _get
        self._function_chain = FunctionChain
        self._chainable_fn = ChainableFn
    
    def forward(self, source: Any) -> Any:
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
    
    def reverse(self, target: Any) -> Any:  # noqa: ARG002
        """
        Reverse transformation (target to source).
        
        Note: This is only possible for simple mappings. Complex transformations
        with functions or conditions are generally not reversible.
        """
        raise NotImplementedError(
            "View reverse transformation is not implemented. "
            "For reversible mappings, consider using BijectiveView (future feature)."
        )
    
    def can_reverse(self) -> bool:
        """View generally cannot reverse complex transformations."""
        return False
    
    def _validate_mapping(self) -> dict[str, list[str]]:
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
# A `BijectiveView` is a `View` that is bijective, i.e. it has a one-to-one mapping in both directions
# """
# class BijectiveView(View):

#     # Defines a `put` method and save state for reverse lookup
#     def put(...) -> ...:
#         ...
#     ...