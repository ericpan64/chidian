
from copy import deepcopy
from typing import Any, Callable

from .seeds import SEED, DROP, KEEP, DropLevel

"""
A `DictPiper` processes data mappings and consumes SEEDs to apply transformations.

As a Piper processes data, it will consume SEEDs and apply them to the data accordingly.
Uses a two-pass approach: first mapping, then cleanup of DROP/KEEP directives.
"""

class DictPiper:
    def __init__(self, mapping_fn: Callable[[dict[str, Any]], dict[str, Any]], remove_empty: bool = False):
        self.mapping_fn = mapping_fn
        self.remove_empty = remove_empty

    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        """Execute the mapping with SEED processing."""
        # Pass 1: Apply the mapping function
        mapped_data = self.mapping_fn(data)
        
        # Pass 2: Process SEEDs and apply DROP/KEEP logic
        processed_data = self._process_seeds(mapped_data)
        
        # Handle case where entire structure is dropped
        if isinstance(processed_data, DROP):
            return {}  # Return empty dict if entire structure is dropped
        
        # Optional: Remove empty containers
        if self.remove_empty:
            processed_data = self._remove_empty_containers(processed_data)
        
        return processed_data
    
    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Make DictPiper callable."""
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
    
    def _apply_drops(self, data: dict[str, Any], drops: list[tuple[str, DropLevel, list[str]]], path: list[str]) -> dict[str, Any]:
        """Apply DROP operations to a dictionary."""
        result = deepcopy(data)
        
        for key, drop_level, drop_path in drops:
            if drop_level == DropLevel.THIS_OBJECT:
                # DROP.THIS_OBJECT should drop the entire current dict - signal to parent
                return DROP(DropLevel.THIS_OBJECT)
            elif drop_level == DropLevel.PARENT:
                # Should drop the parent of current dict - signal to grandparent
                return DROP(DropLevel.PARENT)
            elif drop_level == DropLevel.GRANDPARENT:
                # Signal to great-grandparent
                return DROP(DropLevel.GRANDPARENT)
            elif drop_level == DropLevel.GREATGRANDPARENT:
                # Check bounds - can't drop beyond root
                if len(path) < 3:  # Need at least 3 levels to drop greatgrandparent
                    raise RuntimeError("Cannot drop GREATGRANDPARENT: not enough parent levels")
                return DROP(DropLevel.GREATGRANDPARENT)
        
        return result
    
    def _apply_list_drops(self, data: list[Any], drops: list[tuple[int, DropLevel, list[str]]], path: list[str]) -> list[Any]:
        """Apply DROP operations to a list."""
        if not drops:
            return data
        
        for index, drop_level, drop_path in drops:
            if drop_level == DropLevel.THIS_OBJECT:
                # DROP.THIS_OBJECT should drop the entire current list - signal to parent
                return DROP(DropLevel.THIS_OBJECT)
            elif drop_level == DropLevel.PARENT:
                # Should drop the parent of current list - signal to grandparent
                return DROP(DropLevel.PARENT)
            elif drop_level == DropLevel.GRANDPARENT:
                # Signal to great-grandparent
                return DROP(DropLevel.GRANDPARENT)
            elif drop_level == DropLevel.GREATGRANDPARENT:
                # Check bounds - can't drop beyond root
                if len(path) < 3:  # Need at least 3 levels to drop greatgrandparent
                    raise RuntimeError("Cannot drop GREATGRANDPARENT: not enough parent levels")
                return DROP(DropLevel.GREATGRANDPARENT)
        
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