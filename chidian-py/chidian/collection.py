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
                # Store items by index in parent dict
                for i, item in enumerate(items):
                    self[str(i)] = item
            elif isinstance(items, dict):
                self._items = list(items.values())
                # Store items by their original keys
                for key, item in items.items():
                    self[key] = item
    
    def get(self, key: str, default: Any = None, apply: Optional[Callable] = None, strict: bool = False) -> Any:
        """
        Get a single value using path-based access (for collection-wide queries use select()).
        
        Examples:
            collection.get("patient_123")         # Get specific item
            collection.get("0.patient.id")        # Get nested value
            collection.get("$0")                  # Get all items as list
            collection.get("$0[2].status")        # Get from third item
        
        Args:
            key: Path to retrieve ($0 references the ordered items list)
            default: Default if not found
            apply: Optional transform function
            strict: Raise errors instead of returning None
        """
        # Handle special $0 syntax for accessing the ordered items
        if key == "$0":
            result = self._items
            return apply(result) if apply else result
        elif key.startswith("$0[") or key.startswith("$0."):
            # Replace $0 with the items list for get_rs to process
            modified_key = key[2:]  # Remove "$0"
            return get_rs(self._items, modified_key, default=default, apply=apply, strict=strict)
        
        # For all other queries, use get_rs directly on the dict
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
    
    def add(self, item: dict[str, Any], key: Optional[str] = None) -> None:
        """
        Add an item to the collection.
        
        Args:
            item: Dictionary to add
            key: Optional key (auto-generated from index if not provided)
        """
        self._items.append(item)
        
        if key is None:
            # Use index as key if not provided
            key = str(len(self) - 1)
        
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
        
        # Preserve keys for filtered items
        result = DataCollection()
        for key, value in self.items():
            if value in filtered_items:
                result[key] = value
                
        result._items = filtered_items
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
        
        # Create new collection with same structure
        if isinstance(self.keys(), dict):
            items_dict = {k: transformed[i] for i, k in enumerate(self.keys())}
            return DataCollection(items_dict)
        else:
            return DataCollection(transformed)
    
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