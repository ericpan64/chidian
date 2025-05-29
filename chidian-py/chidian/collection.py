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
    
    def get_all(self, path: str, default: Any = None, apply: Optional[Callable] = None, strict: bool = False) -> list:
        """
        Apply get_rs to extract a path from all items in the collection.
        
        Examples:
            collection.get_all("patient.id")      # Get patient.id from all items
            collection.get_all("name")             # Get name from all items
            collection.get_all("status", default="unknown")  # With default
        
        Args:
            path: Path to extract from each item
            default: Default value for items missing this path
            apply: Optional transform function to apply to each result
            strict: If True, raise errors instead of returning default
            
        Returns:
            List of extracted values (one per item)
        """
        results = []
        for item in self._items:
            value = get_rs(item, path, default=default, apply=apply, strict=strict)
            results.append(value)
        return results
    
    def select(self, fields: str = "*", where: Optional[Callable[[dict], bool]] = None, flat: bool = False, sparse: str = "preserve"):
        """
        Select fields from the collection with optional filtering and sparse data handling.
        
        Examples:
            collection.select("name, age")                    # Select specific fields, None for missing
            collection.select("patient.name, patient.id")     # Nested paths
            collection.select("patient.*")                    # All from nested object
            collection.select("*", where=lambda x: x.get("active") is not None)
            collection.select("name", flat=True)              # Return flat list
            collection.select("patient.id", sparse="filter")  # Filter out items with None values
            
        Args:
            fields: Field specification ("*", "field1, field2", "nested.*")
            where: Optional filter predicate
            flat: If True and single field, return list instead of DataCollection
            sparse: How to handle missing values ("preserve", "filter")
                   - "preserve": Keep items with None values (default for structure preservation)
                   - "filter": Remove items/fields with None values (default for aggregations)
            
        Returns:
            DataCollection with query results, or list if flat=True
        """
        # Parse field specification
        if fields == "*":
            field_list = None  # Keep all fields
        elif ".*" in fields:
            # Handle nested wildcard (e.g., "patient.*")
            nested_path = fields.replace(".*", "")
            field_list = ("wildcard", nested_path)
        else:
            # Parse comma-separated fields
            field_list = [f.strip() for f in fields.split(",")]
        
        # Process each item
        result_items = []
        result_keys = []
        
        for i, item in enumerate(self._items):
            # Apply filter if provided
            if where is not None and not where(item):
                continue
                
            # Extract fields based on specification
            if field_list is None:
                # Keep all fields (*)
                result_item = item.copy()
            elif isinstance(field_list, tuple) and field_list[0] == "wildcard":
                # Handle "nested.*" syntax
                nested_path = field_list[1]
                nested_obj = get_rs(item, nested_path, default=None)
                
                if sparse == "preserve":
                    # Always include, even if None or empty
                    if isinstance(nested_obj, dict):
                        result_item = nested_obj.copy()
                    else:
                        result_item = {} if nested_obj is None else {"value": nested_obj}
                elif sparse == "filter":
                    # Only include if non-empty dict
                    if isinstance(nested_obj, dict) and nested_obj:
                        result_item = nested_obj.copy()
                    else:
                        continue
            elif len(field_list) == 1 and flat:
                # Single field with flat=True - collect for flat list
                value = get_rs(item, field_list[0], default=None)
                if sparse == "preserve":
                    # Include even if None
                    result_items.append(value)
                elif sparse == "filter" and value is not None:
                    # Only include non-None values
                    result_items.append(value)
                continue
            else:
                # Multiple specific fields
                result_item = {}
                for field in field_list:
                    value = get_rs(item, field, default=None)
                    key_name = field.split(".")[-1] if "." in field else field
                    
                    if sparse == "preserve":
                        # Always include the field, even if None
                        result_item[key_name] = value
                    elif sparse == "filter" and value is not None:
                        # Only include non-None values
                        result_item[key_name] = value
                
                # For "filter" mode, skip items with no valid fields
                if sparse == "filter" and not result_item:
                    continue
            
            result_items.append(result_item)
            
            # Preserve the original key for this item
            original_key = None
            for key, val in self.items():
                if val is item:
                    original_key = key
                    break
            result_keys.append(original_key)
        
        # Return based on flat parameter
        if flat and isinstance(field_list, list) and len(field_list) == 1:
            return result_items
        
        # Create new DataCollection preserving structure
        result = DataCollection()
        result._items = result_items
        
        # Preserve original keys
        for i, (item, key) in enumerate(zip(result_items, result_keys)):
            if key is not None:
                if key.startswith("$") and key[1:].isdigit():
                    # Reindex numeric keys based on new position
                    result[f"${i}"] = item
                else:
                    # Preserve custom keys
                    result[key] = item
            else:
                # Fallback to numeric key
                result[f"${i}"] = item
        
        return result

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