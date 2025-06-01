"""
Unified data mapping interface that supports both unidirectional (View) and bidirectional (Lens) transformations.
"""

from typing import Any, Optional, Type, TypeVar, Tuple, Union, Callable
from pydantic import BaseModel
from .recordset import RecordSet
from .lib import put

# Type variables for generic models
SourceT = TypeVar('SourceT', bound=BaseModel)
TargetT = TypeVar('TargetT', bound=BaseModel)


class DataMapping:
    """
    A unified data mapping interface for transformations between Pydantic models.
    
    Supports two modes:
    - View (unidirectional): Complex mappings with functions, conditions, etc.
    - Lens (bidirectional): Simple string-to-string path mappings that can be reversed
    """
    
    def __init__(
        self,
        source_model: Type[SourceT],
        target_model: Type[TargetT], 
        mapping: Union[Callable[[dict], dict], dict[str, Any]],
        bidirectional: bool = False,
        strict: bool = True,
        metadata: Optional[dict] = None
    ):
        """
        Initialize a data mapping between Pydantic models.
        
        Args:
            source_model: Source Pydantic BaseModel class
            target_model: Target Pydantic BaseModel class
            mapping: Either a callable that transforms source dict to target dict,
                    or a dict of field mappings (for bidirectional mode)
            bidirectional: If True, enables bidirectional mode with reversible mappings
            strict: If True, validate against models and fail on errors
            metadata: Optional metadata about the mapping
        """
        # Validate that models are Pydantic v2 BaseModels
        if not hasattr(source_model, 'model_fields'):
            raise TypeError(f"source_model must be a Pydantic v2 BaseModel, got {type(source_model)}")
        if not hasattr(target_model, 'model_fields'):
            raise TypeError(f"target_model must be a Pydantic v2 BaseModel, got {type(target_model)}")
        
        self.source_model = source_model
        self.target_model = target_model
        self.mapping = mapping
        self.bidirectional = bidirectional
        self.strict = strict
        self.metadata = metadata or {}
        
        # Import dependencies
        from .chidian_rs import get as _get
        from .partials import FunctionChain, ChainableFn
        self._get = _get
        self._function_chain = FunctionChain
        self._chainable_fn = ChainableFn
        
        # Validate mapping type based on mode
        if self.bidirectional:
            # Bidirectional mode requires dict mappings for reversibility
            if not isinstance(mapping, dict):
                raise TypeError("Bidirectional mappings must be dict of string-to-string paths")
            
            # Validate all mappings are string-to-string for reversibility
            for source_path, target_path in mapping.items():
                if not isinstance(source_path, str) or not isinstance(target_path, str):
                    raise TypeError("Bidirectional mappings must be string-to-string paths")
            
            # Pre-compute reverse mappings
            self._reverse_mappings = {v: k for k, v in mapping.items()}
            
            # Validate reversibility in strict mode
            if strict and not self.is_reversible():
                duplicates = [v for v in mapping.values() if list(mapping.values()).count(v) > 1]
                raise ValueError(f"Mapping is not reversible - duplicate target paths: {duplicates}")
        else:

            # Unidirectional mode - supports both callable and dict mappings
            if callable(mapping):
                # Callable mapping - store as mapping function
                self.mapping_fn = mapping
            elif isinstance(mapping, dict):
                # Dict mapping - validate in strict mode
                if self.strict:
                    validation_issues = self._validate_mapping()
                    if validation_issues['missing_required_fields']:
                        raise ValueError(
                            f"Missing required target fields in mapping: {validation_issues['missing_required_fields']}"
                        )
            else:
                raise TypeError("Mapping must be callable or dict for unidirectional mode")
    
    def forward(self, source: Union[SourceT, dict]) -> Union[TargetT, Tuple[TargetT, RecordSet]]:
        """
        Transform source model to target model.
        
        Args:
            source: Instance of source_model or dict
            
        Returns:
            - Unidirectional mode: Instance of target_model
            - Bidirectional mode: Tuple of (target_model, spillover RecordSet)
        """
        # Validate/convert input
        if not isinstance(source, self.source_model):
            if self.strict:
                raise TypeError(f"Expected {self.source_model.__name__}, got {type(source).__name__}")
            # Try to convert if not strict
            source = self.source_model.model_validate(source)
        
        # Convert to dict for processing
        source_dict = source.model_dump() if hasattr(source, 'model_dump') else source
        
        if self.bidirectional:
            # Bidirectional mode - simple path mappings with spillover tracking
            target_data = {}
            mapped_paths = set()
            
            for source_path, target_path in self.mapping.items():
                value = self._get(source_dict, source_path)
                if value is not None:
                    target_data = put(target_data, target_path, value, strict=False)
                    mapped_paths.add(source_path)
            
            # Create target and spillover
            target = self.target_model.model_validate(target_data)
            spillover_data = self._collect_spillover(source_dict, mapped_paths)
            spillover = RecordSet([spillover_data]) if spillover_data else RecordSet()
            
            return target, spillover
        else:
            # Unidirectional mode
            if hasattr(self, 'mapping_fn'):
                # Callable mapping - apply function
                try:
                    result = self.mapping_fn(source_dict)
                    # Validate and construct target model
                    return self.target_model.model_validate(result)
                except Exception as e:
                    if self.strict:
                        raise ValueError(f"Error in mapping function: {e}")
                    # Return dict as fallback
                    return result
            else:
                # Dict mapping - process field by field
                result = {}
                
                for target_field, mapping_spec in self.mapping.items():
                    try:
                        result[target_field] = self._process_mapping(source_dict, mapping_spec)
                    except Exception as e:
                        if self.strict:
                            raise ValueError(f"Error mapping field '{target_field}': {e}")
                        # In non-strict mode, skip failed mappings
                        continue
                
                # Validate and construct target model
                try:
                    return self.target_model.model_validate(result)
                except Exception as e:
                    if self.strict:
                        raise ValueError(f"Failed to construct {self.target_model.__name__}: {e}")
                    # Return dict as fallback
                    return result

    def reverse(self, target: TargetT, spillover: Optional[RecordSet] = None) -> SourceT:
        """
        Reverse transformation (target to source). Only available in bidirectional mode.
        
        Args:
            target: Instance of target_model
            spillover: Optional spillover data from forward transformation
            
        Returns:
            Instance of source_model
        """
        if not self.bidirectional:
            raise RuntimeError("reverse() is only available in bidirectional mode")
        
        if not self.is_reversible():
            raise ValueError("This mapping cannot reverse - mappings are not bidirectional")
        
        # Convert target to dict
        target_dict = target.model_dump()
        
        # Apply reverse mappings
        source_data = {}
        for target_path, source_path in self._reverse_mappings.items():
            value = self._get(target_dict, target_path)
            if value is not None:
                source_data = put(source_data, source_path, value, strict=False)
        
        # Merge spillover if provided
        if spillover and len(spillover) > 0:
            spillover_data = spillover._items[0]
            source_data = self._merge_dicts(source_data, spillover_data)
        
        # Create source model
        return self.source_model.model_validate(source_data)
    
    def is_reversible(self) -> bool:
        """Check if this mapping can be reversed (bidirectional mode only)."""
        if not self.bidirectional:
            return False
        
        # Check for duplicate target paths (many-to-one mappings)
        target_paths = list(self.mapping.values())
        return len(target_paths) == len(set(target_paths))
    
    def can_reverse(self) -> bool:
        """Alias for is_reversible() for backward compatibility."""
        return self.is_reversible()
    
    # Private helper methods
    
    def _process_mapping(self, source: dict, mapping_spec: Any) -> Any:
        """Process a single mapping specification (unidirectional mode)."""
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
    
    def _collect_spillover(self, source_dict: dict, mapped_paths: set[str]) -> dict:
        """Collect unmapped fields for spillover (bidirectional mode)."""
        spillover = {}
        
        def collect_unmapped(data: dict, path: str = "", target_dict = None):
            if target_dict is None:
                target_dict = spillover
                
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if this exact path was mapped
                path_mapped = current_path in mapped_paths
                
                if not path_mapped:
                    if isinstance(value, dict):
                        # Add nested dict to spillover
                        target_dict[key] = {}
                        collect_unmapped(value, current_path, target_dict[key])
                        # Remove empty dicts
                        if not target_dict[key]:
                            del target_dict[key]
                    else:
                        target_dict[key] = value
        
        collect_unmapped(source_dict)
        return spillover
    
    def _merge_dicts(self, target: dict, source: dict) -> dict:
        """Deep merge two dictionaries."""
        result = target.copy()
        
        for key, value in source.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_mapping(self) -> dict[str, list[str]]:
        """Validate the mapping against source and target models (unidirectional mode with dict mapping)."""
        issues = {
            'missing_required_fields': [],
            'unknown_target_fields': [],
            'invalid_source_fields': []
        }
        
        # Skip validation for callable mappings
        if hasattr(self, 'mapping_fn'):
            return issues

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
        
        return issues
    
    def _get_model_fields(self, model: type) -> dict:
        """Get fields from Pydantic v2 model."""
        return getattr(model, 'model_fields', {})
    
    def _is_field_required(self, field_info) -> bool:
        """Check if field is required in Pydantic v2."""
        return field_info.is_required()