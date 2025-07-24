from typing import Any, Callable, Iterator, Optional, Union

from .core import get

"""
A `Table` is a lightweight, sparse table implementation that treats a collection of dictionaries as rows in a table.

Each dictionary represents a row with potentially different keys (columns), making it ideal for heterogeneous,
nested data. Provides a middle ground between the strictness of DataFrames and raw list[dict]/dict[str, dict].

Supports path-based queries, filtering, mapping, and other functional operations.
"""


class Table(dict):
    def __init__(
        self,
        rows: Union[list[dict[str, Any]], dict[str, dict[str, Any]], None] = None,
        **kwargs,
    ):
        """
        Initialize a Table from rows.

        Args:
            rows: Either:
                - list[dict]: Each dict is a row, auto-keyed by index ($0, $1, ...)
                - dict[str, dict]: Pre-keyed rows (keys preserved)
                - None: Empty table
            **kwargs: Additional dict initialization parameters
        """
        super().__init__(**kwargs)
        self._rows: list[dict[str, Any]] = []
        self._row_keys: dict[str, int] = {}  # Maps row keys to indices

        # Initialize rows based on input type
        if rows is not None:
            if isinstance(rows, list):
                self._rows = rows
                # Store rows by index using $-syntax
                for i, row in enumerate(rows):
                    key = f"${i}"
                    self[key] = row
                    self._row_keys[key] = i
            elif isinstance(rows, dict):
                self._rows = list(rows.values())
                # Store rows by their original keys
                for i, (key, row) in enumerate(rows.items()):
                    # Ensure keys start with $ for consistency
                    if not key.startswith("$"):
                        key = f"${key}"
                    self[key] = row
                    self._row_keys[key] = i

    def get(self, path: str, default: Any = None) -> Union[Any, list[Any]]:
        """
        Extract values from rows using a path expression.

        If path starts with $, extracts from a specific row only.
        Otherwise, extracts from all rows.

        Uses the existing chidian.core.get() engine to navigate nested structures.

        Args:
            path: Path expression:
                  - "$0.name" or "$bob.name": Extract from specific row
                  - "name" or "patient.id": Extract from all rows
            default: Value to use when path doesn't exist

        Returns:
            - Single value when using $-prefixed path for specific row
            - List of values (one per row) when extracting from all rows

        Examples:
            >>> t = Table([
            ...     {"name": "John", "age": 30},
            ...     {"name": "Jane", "age": 25},
            ...     {"name": "Bob"}  # Note: no age
            ... ])
            >>> t.get("name")
            ["John", "Jane", "Bob"]
            >>> t.get("$0.name")
            "John"
            >>> t.get("$1.age")
            25
            >>> t.get("$2.age", default=0)
            0
            >>> t.append({"name": "Alice"}, custom_key="alice")
            >>> t.get("$alice.name")
            "Alice"
        """
        # Check if path starts with $ (specific row access)
        if path.startswith("$"):
            # Extract row key and remaining path
            parts = path.split(".", 1)
            row_key = parts[0]

            # Check if this key exists
            if row_key not in self:
                return default

            # Get the specific row
            row = self[row_key]

            # If there's a remaining path, extract from the row
            if len(parts) > 1:
                return get(row, parts[1], default=default)
            else:
                # Just the row key itself, return the whole row
                return row

        # Original behavior: extract from all rows
        results = []
        for row in self._rows:
            value = get(row, path, default=default)
            results.append(value)
        return results

    @property
    def columns(self) -> set[str]:
        """
        Return the union of all keys across all rows.

        This represents the "sparse columns" of the table.

        Examples:
            >>> t = Table([
            ...     {"name": "John", "age": 30},
            ...     {"name": "Jane", "city": "NYC"}
            ... ])
            >>> t.columns
            {"name", "age", "city"}
        """
        all_keys: set[str] = set()
        for row in self._rows:
            all_keys.update(row.keys())
        return all_keys

    def to_list(self) -> list[dict[str, Any]]:
        """Return rows as a plain list of dicts."""
        return self._rows.copy()

    def to_dict(self) -> dict[str, dict[str, Any]]:
        """Return rows as a dict keyed by row identifiers."""
        return dict(self)

    def append(self, row: dict[str, Any], custom_key: Optional[str] = None) -> None:
        """
        Add a new row to the table.

        This operation may expand the logical column set if the new row
        contains keys not seen in existing rows.

        Args:
            row: Dictionary representing the new row
            custom_key: Optional row identifier (defaults to $n where n is the index)
                        If provided and doesn't start with $, will be prefixed with $

        Examples:
            >>> t = Table([{"name": "John"}])
            >>> t.append({"name": "Jane", "age": 25})  # Adds 'age' column
            >>> t.append({"name": "Bob", "city": "NYC"}, custom_key="bob")  # Adds 'city' column
            >>> len(t)
            3
        """
        self._rows.append(row)

        if custom_key is None:
            # Use $-prefixed index as key
            key = f"${len(self._rows) - 1}"
        else:
            # Ensure custom keys start with $
            if not custom_key.startswith("$"):
                key = f"${custom_key}"
            else:
                key = custom_key

        self[key] = row
        self._row_keys[key] = len(self._rows) - 1

    def filter(self, predicate: Union[str, Callable[[dict], bool]]) -> "Table":
        """
        Filter rows based on a predicate.

        Args:
            predicate: Either:
                - Callable: Function that takes a row dict and returns bool
                - str: DSL filter expression

        Returns:
            New Table with only rows matching the predicate

        Examples:
            >>> t = Table([{"name": "John", "age": 30}, {"name": "Jane", "age": 25}])
            >>> t.filter(lambda row: row.get("age", 0) > 26)  # Returns Table with just John
            >>> t.filter("age > 26")
            >>> t.filter("status = 'active' AND age >= 18")
            >>> t.filter("addresses[0].city = 'NYC'")
        """
        if isinstance(predicate, str):
            from .lib.filter_parser import parse_filter

            predicate = parse_filter(predicate)

        # Functional predicate implementation
        filtered_rows = [row for row in self._rows if predicate(row)]
        return Table(filtered_rows)

    def map(self, transform: Callable[[dict], dict]) -> "Table":
        """
        Transform each row using the provided function.

        Args:
            transform: Function that takes a row dict and returns a new dict

        Returns:
            New Table with transformed rows

        Examples:
            >>> t = Table([{"name": "john"}, {"name": "jane"}])
            >>> t2 = t.map(lambda row: {**row, "name": row["name"].upper()})
            >>> t2.get("name")
            ["JOHN", "JANE"]

            >>> # Add computed field
            >>> t3 = t.map(lambda row: {**row, "name_length": len(row.get("name", ""))})
        """
        transformed_rows = [transform(row) for row in self._rows]
        return Table(transformed_rows)

    def select(self, query: str) -> "Table":
        """
        Project columns and create a new Table using DSL syntax.

        Args:
            query: DSL column selection expression

        Returns:
            New Table with selected columns

        Examples:
            >>> t.select("name, age")  # Select specific columns
            >>> t.select("*")  # Select all columns
            >>> t.select("patient.id -> patient_id, status")  # Rename column
            >>> t.select("name, addresses[0].city -> primary_city")  # Nested + rename
        """
        from .lib.select_parser import parse_select

        parsed = parse_select(query)

        # Handle wildcard selection
        if parsed == "*":
            return Table(self._rows.copy())

        # Handle column specifications
        if not isinstance(parsed, list):
            # This shouldn't happen based on parse_select implementation
            raise ValueError("Unexpected parser result")

        new_rows = []
        for row in self._rows:
            new_row = {}

            for spec in parsed:
                # Get value using path
                value = get(row, spec.path, default=None)

                # Use rename if specified, otherwise use the last segment of path
                if spec.rename_to:
                    key = spec.rename_to
                else:
                    # Extract last part of path as column name
                    # e.g., "patient.id" -> "id", "name" -> "name"
                    path_parts = spec.path.split(".")
                    # Remove array indices from last part
                    last_part = path_parts[-1].split("[")[0]
                    key = last_part

                new_row[key] = value

            new_rows.append(new_row)

        return Table(new_rows)

    def unique(self, path: str) -> list[Any]:
        """
        Get unique values from a column path.

        Args:
            path: Path expression to extract values from

        Returns:
            List of unique values found at the path
        """
        values = self.get(path)
        seen = set()
        unique_values = []
        for value in values:
            # Handle unhashable types by converting to string for dedup
            try:
                if value not in seen:
                    seen.add(value)
                    unique_values.append(value)
            except TypeError:
                # Unhashable type, use string representation for dedup
                str_value = str(value)
                if str_value not in seen:
                    seen.add(str_value)
                    unique_values.append(value)
        return unique_values

    def group_by(self, path: str) -> dict[Any, "Table"]:
        """
        Group rows by values at a given path.

        Args:
            path: Path expression to group by

        Returns:
            Dictionary mapping unique values to Tables containing matching rows
        """
        groups: dict[Any, list[dict[str, Any]]] = {}

        for row in self._rows:
            group_value = get(row, path, default=None)
            # Handle unhashable types by converting to string
            try:
                hash(group_value)
                key = group_value
            except TypeError:
                key = str(group_value)

            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        return {key: Table(rows) for key, rows in groups.items()}

    def head(self, n: int = 5) -> "Table":
        """
        Return first n rows.

        Args:
            n: Number of rows to return (default 5)

        Returns:
            New Table with first n rows
        """
        return Table(self._rows[:n])

    def tail(self, n: int = 5) -> "Table":
        """
        Return last n rows.

        Args:
            n: Number of rows to return (default 5)

        Returns:
            New Table with last n rows
        """
        return Table(self._rows[-n:])

    def __iter__(self) -> Iterator[dict[str, Any]]:
        """
        Iterate over rows in insertion order.

        Examples:
            >>> t = Table([{"id": 1}, {"id": 2}])
            >>> for row in t:
            ...     print(row["id"])
            1
            2
        """
        return iter(self._rows)

    def __len__(self) -> int:
        """
        Return the number of rows in the table.

        Examples:
            >>> t = Table([{"id": 1}, {"id": 2}])
            >>> len(t)
            2
        """
        return len(self._rows)
