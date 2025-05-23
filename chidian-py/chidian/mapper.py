"""
Mapper class for transforming nested data structures.

This module provides the Mapper class which can transform complex nested
data structures using mapping functions, with support for dropping objects
at various levels and keeping empty values.
"""

from typing import Any, Callable, Dict, List, Union
from .lib.types import _DropSentinel, _Keep, DropLevel
from .dicts.mapper import is_strict_mode


class Mapper:
    """
    Maps data structures using a provided mapping function.
    
    The Mapper can transform complex nested data structures and supports:
    - Dropping objects at various levels (THIS_OBJECT, PARENT, etc.)
    - Keeping empty values that would normally be filtered
    - Strict mode for error handling
    - Automatic removal of empty containers
    """
    
    def __init__(self, mapping_func: Callable[[Any], Any], remove_empty: bool = True):
        """
        Initialize the Mapper.
        
        Args:
            mapping_func: Function that takes source data and returns mapped structure
            remove_empty: Whether to remove empty containers (lists, dicts) from result
        """
        self.mapping_func = mapping_func
        self.remove_empty = remove_empty
    
    def __call__(self, source: Any) -> Any:
        """
        Apply the mapping function to the source data.
        
        Args:
            source: The source data to transform
            
        Returns:
            The transformed data structure
            
        Raises:
            RuntimeError: If a DROP operation targets a level that doesn't exist
            ValueError: If strict mode is enabled and an error occurs during mapping
        """
        try:
            # Apply the mapping function
            mapped = self.mapping_func(source)
            
            # Process the mapped result to handle DROP and KEEP operations
            result = self._process_value(mapped, [])
            
            # Handle top-level drop marker
            if isinstance(result, _DropMarker) and result.levels_up == 0:
                # If the entire structure was dropped, return appropriate empty container
                if isinstance(mapped, dict):
                    return {}
                elif isinstance(mapped, list):
                    return []
                else:
                    return None
            
            return result
            
        except Exception as e:
            if is_strict_mode():
                if isinstance(e, (RuntimeError, ValueError)):
                    raise
                raise ValueError(f"Mapping failed in strict mode: {e}") from e
            raise
    
    def _process_value(self, value: Any, path: List[str]) -> Any:
        """
        Process a value, handling DROP and KEEP operations.
        
        Args:
            value: The value to process
            path: Current path in the data structure (for DROP level calculation)
            
        Returns:
            The processed value
            
        Raises:
            RuntimeError: If DROP targets a level that doesn't exist
        """
        # Handle KEEP wrapper
        if isinstance(value, _Keep):
            return _KeepMarker(value.value)
        
        # Handle DROP sentinel
        if isinstance(value, _DropSentinel):
            return self._handle_drop(value, path)
        
        # Handle dictionaries
        if isinstance(value, dict):
            return self._process_dict(value, path)
        
        # Handle lists
        if isinstance(value, list):
            return self._process_list(value, path)
        
        # Return primitive values as-is
        return value
    
    def _handle_drop(self, drop_sentinel: _DropSentinel, path: List[str]) -> Any:
        """
        Handle a DROP operation.
        
        Args:
            drop_sentinel: The DROP sentinel specifying the level to drop
            path: Current path in the data structure
            
        Returns:
            A special marker indicating what should be dropped
            
        Raises:
            RuntimeError: If the drop level is out of bounds
        """
        level = drop_sentinel.level
        
        if level == DropLevel.THIS_OBJECT:
            return _DropMarker(1)  # Drop the containing object (dict/list)
        elif level == DropLevel.PARENT:
            if len(path) < 1:
                raise RuntimeError("Cannot drop PARENT: no parent exists")
            return _DropMarker(2)  # Drop parent of the containing object
        elif level == DropLevel.GRANDPARENT:
            if len(path) < 2:
                raise RuntimeError("Cannot drop GRANDPARENT: no grandparent exists")
            return _DropMarker(3)  # Drop grandparent of the containing object
        elif level == DropLevel.GREATGRANDPARENT:
            if len(path) < 3:
                raise RuntimeError("Cannot drop GREATGRANDPARENT: no great-grandparent exists")
            return _DropMarker(4)  # Drop great-grandparent of the containing object
        else:
            raise RuntimeError(f"Unknown drop level: {level}")
    
    def _process_dict(self, data: dict, path: List[str]) -> Union[dict, Any]:
        """
        Process a dictionary, handling nested values and DROP operations.
        
        Args:
            data: The dictionary to process
            path: Current path in the data structure
            
        Returns:
            The processed dictionary or a drop marker
        """
        result = {}
        
        for key, value in data.items():
            current_path = path + [key]
            processed_value = self._process_value(value, current_path)
            
            # Handle drop markers
            if isinstance(processed_value, _DropMarker):
                levels_up = processed_value.levels_up
                if levels_up == 0:
                    # Drop this key-value pair entirely
                    continue
                elif levels_up == 1:
                    # Drop this entire dict
                    return _DropMarker(0)
                elif levels_up > 1:
                    # Drop at a higher level - propagate upward
                    return _DropMarker(levels_up - 1)
            
            # Handle keep markers - always include these values
            if isinstance(processed_value, _KeepMarker):
                result[key] = processed_value.value
            # Only add non-empty values (unless remove_empty is False)
            elif not self.remove_empty or not self._is_empty(processed_value):
                result[key] = processed_value
        
        return result
    
    def _process_list(self, data: list, path: List[str]) -> Union[list, Any]:
        """
        Process a list, handling nested values and DROP operations.
        
        Args:
            data: The list to process
            path: Current path in the data structure
            
        Returns:
            The processed list or a drop marker
        """
        result = []
        
        for i, value in enumerate(data):
            current_path = path + [str(i)]
            processed_value = self._process_value(value, current_path)
            
            # Handle drop markers
            if isinstance(processed_value, _DropMarker):
                levels_up = processed_value.levels_up
                if levels_up == 0:
                    # Drop this list item entirely
                    continue
                elif levels_up == 1:
                    # Drop this entire list
                    return _DropMarker(0)
                elif levels_up > 1:
                    # Drop at a higher level - propagate upward
                    return _DropMarker(levels_up - 1)
            
            # Handle keep markers - always include these values
            if isinstance(processed_value, _KeepMarker):
                result.append(processed_value.value)
            # Only add non-empty values (unless remove_empty is False)
            elif not self.remove_empty or not self._is_empty(processed_value):
                result.append(processed_value)
        
        return result
    
    def _is_empty(self, value: Any) -> bool:
        """
        Check if a value is considered empty.
        
        Args:
            value: The value to check
            
        Returns:
            True if the value is empty, False otherwise
        """
        if value is None:
            return True
        if isinstance(value, (dict, list, str)) and len(value) == 0:
            return True
        return False


class _DropMarker:
    """Internal marker for DROP operations."""
    
    def __init__(self, levels_up: int):
        self.levels_up = levels_up
    
    def __repr__(self):
        return f"_DropMarker({self.levels_up})"


class _KeepMarker:
    """Internal marker for KEEP operations."""
    
    def __init__(self, value: Any):
        self.value = value
    
    def __repr__(self):
        return f"_KeepMarker({self.value})"