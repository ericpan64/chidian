"""
Parser for Table select DSL expressions.
"""

from pathlib import Path as PathLib
from typing import Any, List, Optional, Union

from parsimonious import Grammar, NodeVisitor
from parsimonious.nodes import Node

# Load the PEG grammar
SELECT_PEG_PATH = PathLib(__file__).parent / "dsl" / "select.peg"

with open(SELECT_PEG_PATH, "r") as f:
    SELECT_GRAMMAR_TEXT = f.read()

SELECT_GRAMMAR = Grammar(SELECT_GRAMMAR_TEXT)


class ColumnSpec:
    """Represents a single column specification in a select expression."""

    def __init__(self, path: str, rename_to: Optional[str] = None):
        self.path = path
        self.rename_to = rename_to

    def __repr__(self):
        if self.rename_to:
            return f"ColumnSpec({self.path!r} -> {self.rename_to!r})"
        return f"ColumnSpec({self.path!r})"


class SelectVisitor(NodeVisitor):
    """Transforms select DSL parse tree into column specifications."""

    def visit_select_expr(
        self, node: Node, visited_children: List[Any]
    ) -> Union[str, List[ColumnSpec]]:
        """Process the root select expression."""
        # Either star or column_list
        return visited_children[0]

    def visit_star(self, node: Node, visited_children: List[Any]) -> str:
        """Handle wildcard selection."""
        return "*"

    def visit_column_list(
        self, node: Node, visited_children: List[Any]
    ) -> List[ColumnSpec]:
        """Process a list of column specifications."""
        first_spec, rest = visited_children
        specs = [first_spec]

        if rest:
            for comma_group in rest:
                # Extract the spec from the group (might have whitespace)
                spec = None
                for item in comma_group:
                    if isinstance(item, ColumnSpec):
                        spec = item
                        break
                if spec:
                    specs.append(spec)

        return specs

    def visit_column_spec(self, node: Node, visited_children: List[Any]) -> ColumnSpec:
        """Process a single column specification."""
        path, rename_op = visited_children
        rename_to = None

        if rename_op and rename_op[0]:  # Check if rename_op exists and isn't empty
            # Extract the actual rename value from the nested structure
            if isinstance(rename_op[0], list):
                # It's wrapped in a list, extract from it
                for item in rename_op[0]:
                    if isinstance(item, str) and item not in [" ", "\t", "\n", "->"]:
                        rename_to = item
                        break
            elif isinstance(rename_op[0], str):
                rename_to = rename_op[0]

        return ColumnSpec(path, rename_to)

    def visit_rename_op(self, node: Node, visited_children: List[Any]) -> str:
        """Process rename operation."""
        # Extract name from arrow, possible whitespace, name
        for item in visited_children:
            if isinstance(item, str) and item not in ["->", " ", "\t", "\n"]:
                return item
        return visited_children[-1]  # Fallback to last item

    def visit_path(self, node: Node, visited_children: List[Any]) -> str:
        """Process a path expression."""
        # Can be nested_path or simple_name
        result = visited_children[0]
        if isinstance(result, list):
            # It's a simple_name wrapped in a list
            return result[0]
        return result

    def visit_nested_path(self, node: Node, visited_children: List[Any]) -> str:
        """Process a nested path like 'user.profile.name'."""
        base_name, segments = visited_children
        parts = [base_name]

        for dot_segment in segments:
            _, segment = dot_segment
            parts.append(segment)

        return ".".join(parts)

    def visit_path_segment(self, node: Node, visited_children: List[Any]) -> str:
        """Process a path segment with optional array index."""
        name, array_index = visited_children

        if array_index:
            [index_str] = array_index
            return f"{name}{index_str}"

        return name

    def visit_array_index(self, node: Node, visited_children: List[Any]) -> str:
        """Process array index notation."""
        lbrack, index_or_star, rbrack = visited_children
        return f"[{index_or_star}]"

    def visit_simple_name(self, node: Node, visited_children: List[Any]) -> str:
        """Process a simple name."""
        return node.text

    def visit_name(self, node: Node, visited_children: List[Any]) -> str:
        """Process a name (for rename targets)."""
        return node.text

    def visit_number(self, node: Node, visited_children: List[Any]) -> str:
        """Process a number."""
        return node.text

    def generic_visit(self, node: Node, visited_children: List[Any]) -> Any:
        """Default handler."""
        return visited_children or node.text


def parse_select(expr: str) -> Union[str, List[ColumnSpec]]:
    """
    Parse a select expression into column specifications.

    Args:
        expr: The select expression (e.g., "name, age -> years, address.city")

    Returns:
        Either "*" for wildcard or a list of ColumnSpec objects

    Examples:
        >>> parse_select("*")
        "*"
        >>> parse_select("name")
        [ColumnSpec('name')]
        >>> parse_select("patient.id -> patient_id, status")
        [ColumnSpec('patient.id' -> 'patient_id'), ColumnSpec('status')]
    """
    # Trim but preserve internal spaces for proper parsing
    clean_expr = expr.strip()

    if not clean_expr:
        raise ValueError("Empty select expression")

    tree = SELECT_GRAMMAR.parse(clean_expr)
    visitor = SelectVisitor()
    return visitor.visit(tree)
