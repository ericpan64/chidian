
from typing import Any, Callable, TypeVar, Generic, Type, Union, Tuple, Optional, TYPE_CHECKING
from .seeds import SEED, DROP, KEEP, DropLevel

if TYPE_CHECKING:
    from .data_mapping import DataMapping
    from .recordset import RecordSet

"""
A unified `Piper` class that handles both typed and untyped transformations.

As a Piper processes data, it will consume SEEDs and apply them to the data accordingly.
Uses a two-pass approach: first mapping, then cleanup of DROP/KEEP directives.

For untyped (dict-to-dict) transformations, pass dict as both source_type and target_type.
For typed transformations, use a DataMapping instance.
"""

# Type variables for generic typing
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


class Piper(Generic[InputT, OutputT]):
    def __init__(
        self,
        transformer: Union[Callable[[InputT], OutputT], Callable[[dict[str, Any]], dict[str, Any]], 'DataMapping'],
        source_type: Optional[Type[InputT]] = None,
        target_type: Optional[Type[OutputT]] = None,
        remove_empty: bool = False,
        strict: bool = None
    ):
        """
        Initialize a unified Piper for data transformations.
        
        Args:
            transformer: Can be:
                - A callable for dict-to-dict mappings
                - A DataMapping for typed transformations
                - Any callable for custom transformations
            source_type: Source type (None or dict for untyped, specific type for validation)
            target_type: Target type (None or dict for untyped, specific type for validation)
            remove_empty: Whether to remove empty containers (only for dict mode)
            strict: Whether to enforce type validation (inherits from DataMapping if applicable)
        """
        # Import here to avoid circular imports
        from .data_mapping import DataMapping
        
        self.transformer = transformer
        self.remove_empty = remove_empty
        
        # Determine mode and settings based on transformer type
        if isinstance(transformer, DataMapping):
            # Typed transformation with DataMapping
            self.source_type = transformer.source_model
            self.target_type = transformer.target_model
            # Compatibility aliases
            self.input_type = self.source_type
            self.output_type = self.target_type
            self.strict = transformer.strict if strict is None else strict
            
            self._mode = "lens" if transformer.bidirectional else "view"
        else:
            # Dict mode - only supported mode for plain callables
            if source_type is not dict or target_type is not dict:
                raise ValueError(
                    "Piper only supports dict-to-dict transformations or DataMapping objects. "
                    "For dict transformations, use source_type=dict, target_type=dict."
                )
            
            self.source_type = dict
            self.target_type = dict
            # Compatibility aliases
            self.input_type = self.source_type
            self.output_type = self.target_type
            
            self._mode = "dict"
            self.strict = False if strict is None else strict
            # For dict mode, transformer must be callable
            if not callable(transformer):
                raise TypeError("Transformer must be callable for dict mode")
            self.mapping_fn = transformer

    def run(self, data: InputT) -> Union[OutputT, Tuple[OutputT, 'RecordSet']]:
        """Execute the transformation."""
        # Import here to avoid circular imports
        from .recordset import RecordSet
        
        # Type validation in strict mode
        if self.strict and self.source_type and self.source_type not in (dict, type(None)):
            if not isinstance(data, self.source_type):
                raise TypeError(f"Expected {self.source_type.__name__}, got {type(data).__name__}")
        
        # Apply transformation based on mode
        if self._mode == "dict":
            # Dict mode with SEED processing
            # Pass 1: Apply the mapping function
            mapped_data = self.mapping_fn(data)
            
            # Pass 2: Process SEEDs and apply DROP/KEEP logic
            processed_data = self._process_seeds(mapped_data)
            
            # Handle case where entire structure is dropped
            if isinstance(processed_data, DROP):
                return processed_data  # Return DROP object to allow filtering
            
            # Optional: Remove empty containers
            if self.remove_empty:
                processed_data = self._remove_empty_containers(processed_data)
            
            return processed_data
            
        else:
            # DataMapping mode - delegate to transformer
            return self.transformer.forward(data)
    
    def forward(self, data: InputT) -> Union[OutputT, Tuple[OutputT, 'RecordSet']]:
        """Apply forward transformation (alias for run)."""
        return self.run(data)
    
    def reverse(self, output_data: OutputT, spillover: 'RecordSet' = None) -> InputT:
        """Apply reverse transformation (only available for bidirectional DataMapping/Lens)."""
        if self._mode != "lens":
            raise ValueError("Reverse transformation only available for bidirectional mappings")
        
        # Import here to avoid circular imports
        from .recordset import RecordSet
        return self.transformer.reverse(output_data, spillover or RecordSet())
    
    def can_reverse(self) -> bool:
        """Check if this piper supports reverse transformation."""
        return self._mode == "lens" and hasattr(self.transformer, 'can_reverse') and self.transformer.can_reverse()
    
    def __call__(self, data: InputT) -> Union[OutputT, Tuple[OutputT, 'RecordSet']]:
        """Make Piper callable."""
        return self.run(data)
    
    def _process_seeds(self, data: Any, path: list[str] = None) -> Any:
        """Recursively process data structure and handle SEEDs."""
        if path is None:
            path = []
        
        if isinstance(data, dict):
            result = {}
            has_this_object_drop = False
            drops_to_propagate = []
            
            for key, value in data.items():
                current_path = path + [key]
                
                # Check if the raw value is a DROP before processing
                if isinstance(value, DROP):
                    if value.level == DropLevel.THIS_OBJECT:
                        # A DROP.THIS_OBJECT value means drop the containing dict
                        has_this_object_drop = True
                        break
                    # Handle other drop levels
                    if value.level == DropLevel.PARENT:
                        drops_to_propagate.append(DropLevel.PARENT)
                    elif value.level == DropLevel.GRANDPARENT:
                        drops_to_propagate.append(DropLevel.GRANDPARENT)
                    elif value.level == DropLevel.GREATGRANDPARENT:
                        if len(path) < 3:  # Need at least 3 levels to drop greatgrandparent
                            raise RuntimeError("Cannot drop GREATGRANDPARENT: not enough parent levels")
                        drops_to_propagate.append(DropLevel.GREATGRANDPARENT)
                    continue
                
                # Process value recursively
                processed_value = self._process_seeds(value, current_path)
                
                # Handle SEED objects returned from recursive processing
                if isinstance(processed_value, SEED):
                    if isinstance(processed_value, DROP):
                        if processed_value.level == DropLevel.THIS_OBJECT:
                            # Child object was dropped - don't include it
                            continue
                        else:
                            # Adjust level and record for propagation
                            if processed_value.level == DropLevel.PARENT:
                                # Child wants to drop its parent (current dict)
                                has_this_object_drop = True
                                break
                            elif processed_value.level == DropLevel.GRANDPARENT:
                                # Propagate as PARENT
                                drops_to_propagate.append(DropLevel.PARENT)
                            elif processed_value.level == DropLevel.GREATGRANDPARENT:
                                # Propagate as GRANDPARENT
                                drops_to_propagate.append(DropLevel.GRANDPARENT)
                            continue  # Don't add to result
                    elif isinstance(processed_value, KEEP):
                        # KEEP objects unwrap their value
                        result[key] = processed_value.value
                    else:
                        # Other SEEDs should have been processed by now
                        result[key] = processed_value
                else:
                    result[key] = processed_value
            
            # Handle drops
            if has_this_object_drop:
                # This entire dict should be dropped
                return DROP(DropLevel.THIS_OBJECT)
            elif drops_to_propagate:
                # Propagate the highest level drop
                highest_drop = min(drops_to_propagate)  # Lower enum values = higher levels
                return DROP(highest_drop)
            
            return result
            
        elif isinstance(data, list):
            result = []
            has_this_object_drop = False
            drops_to_propagate = []
            
            for i, item in enumerate(data):
                current_path = path + [str(i)]
                
                # Check if the raw item is a DROP before processing
                if isinstance(item, DROP):
                    if item.level == DropLevel.THIS_OBJECT:
                        # A DROP.THIS_OBJECT item means drop the containing list
                        has_this_object_drop = True
                        break
                    # Handle other drop levels
                    if item.level == DropLevel.PARENT:
                        drops_to_propagate.append(DropLevel.PARENT)
                    elif item.level == DropLevel.GRANDPARENT:
                        drops_to_propagate.append(DropLevel.GRANDPARENT)
                    elif item.level == DropLevel.GREATGRANDPARENT:
                        drops_to_propagate.append(DropLevel.GREATGRANDPARENT)
                    continue
                
                # Process item recursively
                processed_item = self._process_seeds(item, current_path)
                
                # Handle SEED objects returned from recursive processing
                if isinstance(processed_item, SEED):
                    if isinstance(processed_item, DROP):
                        if processed_item.level == DropLevel.THIS_OBJECT:
                            # Child object was dropped - don't include it
                            continue
                        else:
                            # Adjust level and record for propagation
                            if processed_item.level == DropLevel.PARENT:
                                # Child wants to drop its parent (current list)
                                has_this_object_drop = True
                                break
                            elif processed_item.level == DropLevel.GRANDPARENT:
                                # Propagate as PARENT
                                drops_to_propagate.append(DropLevel.PARENT)
                            elif processed_item.level == DropLevel.GREATGRANDPARENT:
                                # Propagate as GRANDPARENT
                                drops_to_propagate.append(DropLevel.GRANDPARENT)
                            continue  # Don't add to result
                    elif isinstance(processed_item, KEEP):
                        # KEEP objects unwrap their value
                        result.append(processed_item.value)
                    else:
                        # Other SEEDs should have been processed by now
                        result.append(processed_item)
                else:
                    result.append(processed_item)
            
            # Handle drops
            if has_this_object_drop:
                # This entire list should be dropped
                return DROP(DropLevel.THIS_OBJECT)
            elif drops_to_propagate:
                # Propagate the highest level drop
                highest_drop = min(drops_to_propagate)  # Lower enum values = higher levels
                return DROP(highest_drop)
                
            return result
            
        elif isinstance(data, SEED):
            # Process SEED at this level
            if isinstance(data, DROP):
                return data  # Will be handled by parent
            elif isinstance(data, KEEP):
                return data.value
            else:
                # Other SEEDs should not appear as standalone values
                return data
        else:
            # Primitive value, return as-is
            return data
    
    
    def _remove_empty_containers(self, data: Any) -> Any:
        """Remove empty lists and dictionaries recursively."""
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                cleaned_value = self._remove_empty_containers(value)
                # Keep non-empty containers and non-container values
                if cleaned_value != [] and cleaned_value != {}:
                    result[key] = cleaned_value
            return result
        elif isinstance(data, list):
            result = []
            for item in data:
                cleaned_item = self._remove_empty_containers(item)
                # Keep non-empty containers and non-container values
                if cleaned_item != [] and cleaned_item != {}:
                    result.append(cleaned_item)
            return result
        else:
            return data