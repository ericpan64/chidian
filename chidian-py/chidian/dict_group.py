import json
from typing import Any, Callable, Iterator, Optional, Union

from chidian_rs import get  # type: ignore[attr-defined]

"""
A `DictGroup` is aconvenient wrapper around dict[str, dict] for managing collections of dictionary data.

Think of it as a group of dictionaries where you can `get` (with inter-dictionary references) and `select` from them as a group!

Provides a middle ground between the strictness of DataFrames and raw list[dict]/dict[str, dict],
allowing users to work with collections semantically without worrying about keys and structure.

Supports path-based queries, filtering, mapping, and other functional operations.
"""


class DictGroup(dict):
    def __init__(
        self,
        items: Union[list[dict[str, Any]], dict[str, dict[str, Any]], None] = None,
        **kwargs,
    ):
        """
        Initialize a DictGroup from a list or dict of dictionaries.

        Args:
            items: Either a list of dicts (auto-keyed by index) or a dict of dicts
            **kwargs: Additional dict initialization parameters
        """
        # TODO: does the `self._items` field need to exist -- i.e. could this just be referenced later as `self.values()`?
        #       So don't need the middle abstraction then
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

    def get_all(
        self,
        path: str,
        default: Any = None,
        apply: Optional[Callable] = None,
        strict: bool = False,
    ) -> list:
        """
        Apply get to extract a path from all items in the collection.

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
            value = get(item, path, default=default, apply=apply, strict=strict)
            results.append(value)
        return results

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

    def filter(self, predicate: Callable[[dict], bool]) -> "DictGroup":
        """
        Filter items based on a predicate function.

        Args:
            predicate: Function returning True for items to keep

        Returns:
            New filtered DictGroup
        """
        filtered_items = [item for item in self._items if predicate(item)]

        # Create new collection with filtered items
        result = DictGroup()
        result._items = filtered_items

        # First pass: add all items with numeric keys
        for i, item in enumerate(filtered_items):
            result[f"${i}"] = item

        # Second pass: preserve custom keys
        for key, value in self.items():
            if value in filtered_items and not (
                key.startswith("$") and key[1:].isdigit()
            ):
                # This is a custom key, preserve it
                result[key] = value

        return result

    def map(self, transform: Callable[[dict], dict]) -> "DictGroup":
        """
        Transform each item in the collection.

        Args:
            transform: Function to apply to each item

        Returns:
            New DictGroup with transformed items
        """
        transformed = [transform(item) for item in self._items]

        # Create new collection
        result = DictGroup()
        result._items = transformed

        # Map old items to their indices for lookup
        item_to_index = {id(item): i for i, item in enumerate(self._items)}

        # First pass: add all items with numeric keys
        for i, item in enumerate(transformed):
            result[f"${i}"] = item

        # Second pass: preserve custom keys
        for key, value in self.items():
            if id(value) in item_to_index and not (
                key.startswith("$") and key[1:].isdigit()
            ):
                # This is a custom key, preserve it with the transformed item
                result[key] = transformed[item_to_index[id(value)]]

        return result

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """Iterate over items in the collection."""
        return iter(self._items)

    def __len__(self) -> int:
        """Return number of items in collection."""
        return len(self._items)

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
