"""
Mapper class for applying transformations to data structures with support for DROP and KEEP operations.
"""

from typing import Any, Callable, Dict, List, Union
from .context import get_context
from .types import DropSentinel, DropLevel, Keep


class Mapper:
    """
    A mapper that applies transformations to data structures with support for 
    DROP operations and empty value removal.
    """
    
    def __init__(self, mapping_func: Callable[[Any], Any], remove_empty: bool = True):
        """
        Initialize the mapper.
        
        Args:
            mapping_func: Function that takes data and returns a transformed structure
            remove_empty: Whether to remove empty values from the result
        """
        self.mapping_func = mapping_func
        self.remove_empty = remove_empty
    
    def __call__(self, data: Any) -> Any:
        """
        Apply the mapping function to the data and process DROP operations.
        
        Args:
            data: The input data to transform
            
        Returns:
            The transformed data with DROP operations applied
            
        Raises:
            RuntimeError: If DROP level is out of bounds
            ValueError: If strict mode is enabled and an error occurs
        """
        # Apply the mapping function
        result = self.mapping_func(data)
        
        # Process DROP operations and remove empty values
        processed = self._process_drops(result)
        
        if self.remove_empty:
            processed = self._remove_empty(processed)
            
        return processed
    
    def _process_drops(self, obj: Any, path: List[str] = None) -> Any:
        """
        Process DROP operations in the data structure.
        
        Args:
            obj: The object to process
            path: Current path in the object hierarchy (for error reporting)
            
        Returns:
            The processed object with DROP operations applied
        """
        if path is None:
            path = []
            
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                current_path = path + [key]
                
                if isinstance(value, DropSentinel):
                    # Handle DROP operations
                    drop_level = value.THIS_OBJECT  # Default to THIS_OBJECT
                    if hasattr(value, '__dict__'):
                        # If it's an instance with attributes, find the drop level
                        for attr_name in dir(value):
                            if not attr_name.startswith('_'):
                                attr_value = getattr(value, attr_name)
                                if isinstance(attr_value, DropLevel):
                                    drop_level = attr_value
                                    break
                    
                    # Apply the drop operation
                    if drop_level == DropLevel.THIS_OBJECT:
                        continue  # Skip this key-value pair
                    elif drop_level == DropLevel.PARENT:
                        return None  # Signal to remove parent
                    elif drop_level == DropLevel.GRANDPARENT:
                        if len(path) < 2:
                            raise RuntimeError("DROP.GRANDPARENT used but no grandparent exists")
                        return {"__drop_grandparent__": True}
                    elif drop_level == DropLevel.GREATGRANDPARENT:
                        if len(path) < 3:
                            raise RuntimeError("DROP.GREATGRANDPARENT used but no great-grandparent exists")
                        return {"__drop_greatgrandparent__": True}
                else:
                    # Recursively process the value
                    processed_value = self._process_drops(value, current_path)
                    if processed_value is not None:
                        if isinstance(processed_value, dict):
                            if "__drop_grandparent__" in processed_value:
                                return None  # Remove parent (which is grandparent of the drop)
                            elif "__drop_greatgrandparent__" in processed_value:
                                return {"__drop_grandparent__": True}  # Propagate up
                        result[key] = processed_value
            
            return result
            
        elif isinstance(obj, list):
            result = []
            for i, item in enumerate(obj):
                current_path = path + [str(i)]
                
                if isinstance(item, DropSentinel):
                    # Handle DROP operations in lists
                    drop_level = item.THIS_OBJECT
                    if hasattr(item, '__dict__'):
                        for attr_name in dir(item):
                            if not attr_name.startswith('_'):
                                attr_value = getattr(item, attr_name)
                                if isinstance(attr_value, DropLevel):
                                    drop_level = attr_value
                                    break
                    
                    if drop_level == DropLevel.THIS_OBJECT:
                        continue  # Skip this item
                    elif drop_level == DropLevel.PARENT:
                        return None  # Signal to remove parent
                    # For lists, grandparent and great-grandparent work similarly
                else:
                    processed_item = self._process_drops(item, current_path)
                    if processed_item is not None:
                        if isinstance(processed_item, dict):
                            if "__drop_grandparent__" in processed_item:
                                return None
                            elif "__drop_greatgrandparent__" in processed_item:
                                return {"__drop_grandparent__": True}
                        result.append(processed_item)
            
            return result
        else:
            return obj
    
    def _remove_empty(self, obj: Any) -> Any:
        """
        Remove empty values from the data structure, respecting Keep wrappers.
        
        Args:
            obj: The object to process
            
        Returns:
            The object with empty values removed
        """
        if isinstance(obj, Keep):
            # Keep objects preserve their values even if empty
            return obj.value
            
        elif isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                processed_value = self._remove_empty(value)
                
                # Only include non-empty values
                if not self._is_empty(processed_value):
                    result[key] = processed_value
            
            return result
            
        elif isinstance(obj, list):
            result = []
            for item in obj:
                processed_item = self._remove_empty(item)
                
                # Only include non-empty items
                if not self._is_empty(processed_item):
                    result.append(processed_item)
            
            return result
        else:
            return obj
    
    def _is_empty(self, obj: Any) -> bool:
        """
        Check if an object is considered empty.
        
        Args:
            obj: The object to check
            
        Returns:
            True if the object is empty, False otherwise
        """
        if obj is None:
            return False  # None is not considered empty in this context
        elif isinstance(obj, (dict, list, str)):
            return len(obj) == 0
        else:
            return False 