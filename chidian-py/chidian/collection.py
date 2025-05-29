import json
from typing import Any, Callable, Union, Optional, Iterator
from collections.abc import Iterable

# import pyarrow as pa

from . import get as get_rs

"""
A `DataCollection` is aconvenient wrapper around dict[str, dict] for managing collections of dictionary data.

Think of it as a group of dictionaries where you can `get` (with inter-dictionary references) and `select` from them as a group!

Provides a middle ground between the strictness of DataFrames and raw list[dict]/dict[str, dict],
allowing users to work with collections semantically without worrying about keys and structure.

Supports path-based queries, filtering, mapping, and other functional operations.
"""
class DataCollection(dict):

    def __init__(self, items: Union[list[dict[str, Any]], dict[str, dict[str, Any]], None] = None, **kwargs):
        """
        Initialize a DataCollection from a list or dict of dictionaries.
        
        Args:
            items: Either a list of dicts (auto-keyed by index) or a dict of dicts
            **kwargs: Additional dict initialization parameters
        """
        super().__init__(**kwargs)
        self._items: list[dict[str, Any]] = []
        
        # Initialize items based on input type
        if items is not None:
            if isinstance(items, list):
                self._items = items
                # Store items by index using $-syntax
                for i, item in enumerate(items):
                    self[f"${i}"] = item
            elif isinstance(items, dict):
                self._items = list(items.values())
                # Store items by their original keys
                for key, item in items.items():
                    self[key] = item
    
    def get(self, key: str, default: Any = None, apply: Optional[Callable] = None, strict: bool = False) -> Any:
        """
        Get a single value using path-based access (for collection-wide queries use select()).
        
        Examples:
            collection.get("$0")                  # Get first item
            collection.get("$2.patient.id")       # Get nested value from third item
            collection.get("$my_key.status")      # Get from named item
        
        Args:
            key: Path to retrieve (use $n for index, $key for named items)
            default: Default if not found
            apply: Optional transform function
            strict: Raise errors instead of returning None
        """
        # Handle $-based syntax
        if key.startswith("$"):
            # Split at first dot to separate the reference from the path
            parts = key.split(".", 1)
            ref = parts[0]
            path = parts[1] if len(parts) > 1 else None
            
            # Check if ref is a number (index access)
            try:
                index = int(ref[1:])  # Remove $ and convert
                if 0 <= index < len(self._items):
                    item = self._items[index]
                    if path:
                        return get_rs(item, path, default=default, apply=apply, strict=strict)
                    else:
                        return apply(item) if apply else item
                else:
                    return default
            except ValueError:
                # Not a number, treat as key access
                if ref in self:
                    item = self[ref]
                    if path:
                        return get_rs(item, path, default=default, apply=apply, strict=strict)
                    else:
                        return apply(item) if apply else item
                else:
                    return default
        
        # For non-$ queries, use get_rs directly on the dict
        return get_rs(self, key, default=default, apply=apply, strict=strict)
    
    def select(self, key: str = None, where: Optional[Callable[[dict], bool]] = None) -> "DataCollection":
        """
        Query across all items in the collection.
        
        Examples:
            collection.select()                   # All items
            collection.select("patient")          # Extract patient from each item
            collection.select("data.status")      # Extract nested values
            collection.select(where=lambda x: x.get("active"))  # Filter items
            
        Args:
            key: Optional path to extract from each item
            where: Optional filter predicate
            
        Returns:
            New DataCollection with results
        """
        selected_items = []
        
        for item in self._items:
            # Apply filter if provided
            if where is not None and not where(item):
                continue
                
            if key:
                # Extract the specified path from each item
                value = get_rs(item, key, default=None)
                if value is not None:
                    # Only include dict values in the new collection
                    if isinstance(value, dict):
                        selected_items.append(value)
            else:
                # No path specified, include the whole item
                selected_items.append(item)
        
        return DataCollection(selected_items)

    def to_json(self, as_list: bool = False, indent: Optional[int] = None) -> str:
        """
        Export collection as JSON string.
        
        Args:
            as_list: Return as array (True) or dict (False)
            indent: Pretty-print indentation
        """
        if as_list:
            return json.dumps(self._items, indent=indent, default=str)
        else:
            # Return as dict with current keys
            return json.dumps(dict(self), indent=indent, default=str)
    
    def append(self, item: dict[str, Any], key: Optional[str] = None) -> None:
        """
        Append an item to the collection (list-like behavior).
        
        Args:
            item: Dictionary to add
            key: Optional key for named access (defaults to $n where n is index)
        """
        self._items.append(item)
        
        if key is None:
            # Use $-prefixed index as key
            key = f"${len(self._items) - 1}"
        else:
            # Ensure custom keys start with $
            if not key.startswith("$"):
                key = f"${key}"
        
        self[key] = item
    
    def filter(self, predicate: Callable[[dict], bool]) -> "DataCollection":
        """
        Filter items based on a predicate function.
        
        Args:
            predicate: Function returning True for items to keep
            
        Returns:
            New filtered DataCollection
        """
        filtered_items = [item for item in self._items if predicate(item)]
        
        # Create new collection with filtered items
        result = DataCollection()
        result._items = filtered_items
        
        # First pass: add all items with numeric keys
        for i, item in enumerate(filtered_items):
            result[f"${i}"] = item
        
        # Second pass: preserve custom keys
        for key, value in self.items():
            if value in filtered_items and not (key.startswith("$") and key[1:].isdigit()):
                # This is a custom key, preserve it
                result[key] = value
        
        return result
    
    def map(self, transform: Callable[[dict], dict]) -> "DataCollection":
        """
        Transform each item in the collection.
        
        Args:
            transform: Function to apply to each item
            
        Returns:
            New DataCollection with transformed items
        """
        transformed = [transform(item) for item in self._items]
        
        # Create new collection
        result = DataCollection()
        result._items = transformed
        
        # Map old items to their indices for lookup
        item_to_index = {id(item): i for i, item in enumerate(self._items)}
        
        # First pass: add all items with numeric keys
        for i, item in enumerate(transformed):
            result[f"${i}"] = item
        
        # Second pass: preserve custom keys
        for key, value in self.items():
            if id(value) in item_to_index and not (key.startswith("$") and key[1:].isdigit()):
                # This is a custom key, preserve it with the transformed item
                result[key] = transformed[item_to_index[id(value)]]
        
        return result
    
    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over items in the collection."""
        return iter(self._items)
    
    def __len__(self) -> int:
        """Return number of items in collection."""
        return len(self._items)
    
    # def to_table(self) -> pa.Table:
    #     """
    #     Converts the collection to a PyArrow table. 
    #     Flattens nested structures into columns.
    #     """
    #     import pyarrow as pa
    #     
    #     # Collect all unique paths
    #     all_paths = set()
    #     for item in self._items:
    #         paths = self._extract_paths(item)
    #         all_paths.update(paths)
    #     
    #     # Build columns
    #     columns = {}
    #     for path in sorted(all_paths):
    #         values = []
    #         for item in self._items:
    #             value = get_rs(item, path)
    #             values.append(value)
    #         columns[path.replace(".", "_")] = values
    #     
    #     return pa.table(columns)
    
    def _extract_paths(self, obj: Any, prefix: str = "") -> set[str]:
        """Extract all paths from a nested dict."""
        paths = set()
        
        if isinstance(obj, dict):
            for key, value in obj.items():
                new_prefix = f"{prefix}.{key}" if prefix else key
                paths.add(new_prefix)
                
                if isinstance(value, (dict, list)):
                    paths.update(self._extract_paths(value, new_prefix))
        elif isinstance(obj, list) and obj:
            # Just handle first item for schema
            if isinstance(obj[0], dict):
                paths.update(self._extract_paths(obj[0], prefix))
        
        return paths