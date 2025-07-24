"""
Parser for Table filter DSL expressions.
"""

from pathlib import Path as PathLib
from typing import Any, Callable, List, Union

from parsimonious import Grammar, NodeVisitor
from parsimonious.nodes import Node

from ..core import get

# Load the PEG grammar
FILTER_PEG_PATH = PathLib(__file__).parent / "dsl" / "filter.peg"

with open(FILTER_PEG_PATH, "r") as f:
    FILTER_GRAMMAR_TEXT = f.read()

FILTER_GRAMMAR = Grammar(FILTER_GRAMMAR_TEXT)


class FilterVisitor(NodeVisitor):
    """Transforms filter DSL parse tree into callable predicates."""

    def visit_filter_expr(
        self, node: Node, visited_children: List[Any]
    ) -> Callable[[dict], bool]:
        """Process the root filter expression."""
        return visited_children[0]

    def visit_or_expr(
        self, node: Node, visited_children: List[Any]
    ) -> Callable[[dict], bool]:
        """Process OR expressions."""
        first_expr, rest = visited_children

        if not rest:
            return first_expr

        # Build OR chain
        def or_predicate(row: dict) -> bool:
            if first_expr(row):
                return True
            for or_part in rest:
                # Extract expr from: whitespace or_op whitespace and_expr
                expr = or_part[3] if len(or_part) > 3 else or_part[-1]
                if expr(row):
                    return True
            return False

        return or_predicate

    def visit_and_expr(
        self, node: Node, visited_children: List[Any]
    ) -> Callable[[dict], bool]:
        """Process AND expressions."""
        first_comp, rest = visited_children

        if not rest:
            return first_comp

        # Build AND chain
        def and_predicate(row: dict) -> bool:
            if not first_comp(row):
                return False
            for and_part in rest:
                # Extract comp from: whitespace and_op whitespace comparison
                comp = and_part[3] if len(and_part) > 3 else and_part[-1]
                if not comp(row):
                    return False
            return True

        return and_predicate

    def visit_comparison(
        self, node: Node, visited_children: List[Any]
    ) -> Callable[[dict], bool]:
        """Process a single comparison."""
        # Extract path, op, value from: path whitespace op whitespace value
        path = visited_children[0]
        op = visited_children[2]
        value = visited_children[4]

        def compare(row: dict) -> bool:
            try:
                row_value = get(row, path)

                # Handle different operators
                if op == "=":
                    return row_value == value
                elif op == "!=":
                    return row_value != value
                elif op == ">":
                    return row_value > value
                elif op == "<":
                    return row_value < value
                elif op == ">=":
                    return row_value >= value
                elif op == "<=":
                    return row_value <= value
                elif op == "CONTAINS":
                    # String contains or list contains
                    if isinstance(row_value, str) and isinstance(value, str):
                        return value in row_value
                    elif isinstance(row_value, list):
                        return value in row_value
                    return False
                elif op == "IN":
                    # Value in list
                    return row_value in value if isinstance(value, list) else False

                return False
            except Exception:
                # Path not found or comparison failed
                return False

        return compare

    def visit_compare_op(self, node: Node, visited_children: List[Any]) -> str:
        """Process comparison operator."""
        op = visited_children[0]
        # Normalize to uppercase for CONTAINS/IN
        if isinstance(op, str) and op.upper() in ["CONTAINS", "IN"]:
            return op.upper()
        return op

    def visit_path(self, node: Node, visited_children: List[Any]) -> str:
        """Process a path expression."""
        result = visited_children[0]
        if isinstance(result, list):
            return result[0]
        return result

    def visit_nested_path(self, node: Node, visited_children: List[Any]) -> str:
        """Process a nested path."""
        base_name, segments = visited_children
        parts = [base_name]

        for dot_segment in segments:
            _, segment = dot_segment
            parts.append(segment)

        return ".".join(parts)

    def visit_path_segment(self, node: Node, visited_children: List[Any]) -> str:
        """Process a path segment."""
        name, array_index = visited_children

        if array_index:
            [index_str] = array_index
            return f"{name}{index_str}"

        return name

    def visit_array_index(self, node: Node, visited_children: List[Any]) -> str:
        """Process array index."""
        lbrack, index_content, rbrack = visited_children
        return f"[{index_content}]"

    def visit_index_content(self, node: Node, visited_children: List[Any]) -> str:
        """Process index content."""
        return visited_children[0]

    def visit_value(self, node: Node, visited_children: List[Any]) -> Any:
        """Process a value."""
        return visited_children[0]

    def visit_string(self, node: Node, visited_children: List[Any]) -> str:
        """Process string value."""
        # Either single_quoted or double_quoted
        return visited_children[0]

    def visit_single_quoted(self, node: Node, visited_children: List[Any]) -> str:
        """Process single quoted string."""
        _, content, _ = visited_children
        return content

    def visit_double_quoted(self, node: Node, visited_children: List[Any]) -> str:
        """Process double quoted string."""
        _, content, _ = visited_children
        return content

    def visit_string_content_single(
        self, node: Node, visited_children: List[Any]
    ) -> str:
        """Process single quoted string content."""
        return node.text

    def visit_string_content_double(
        self, node: Node, visited_children: List[Any]
    ) -> str:
        """Process double quoted string content."""
        return node.text

    def visit_number(
        self, node: Node, visited_children: List[Any]
    ) -> Union[int, float]:
        """Process numeric value."""
        text = node.text
        if "." in text:
            return float(text)
        return int(text)

    def visit_boolean(self, node: Node, visited_children: List[Any]) -> bool:
        """Process boolean value."""
        value = visited_children[0]
        return value.upper() == "TRUE"

    def visit_null(self, node: Node, visited_children: List[Any]) -> None:
        """Process null value."""
        return None

    def visit_list_value(self, node: Node, visited_children: List[Any]) -> List[Any]:
        """Process list value."""
        lbrack, content, rbrack = visited_children

        if not content:
            return []

        [values] = content
        if not isinstance(values, list):
            return [values]

        # Extract first value and rest
        result = []
        if len(values) >= 1:
            result.append(values[0])

        if len(values) > 1 and values[1]:
            for comma_value in values[1]:
                _, value = comma_value
                result.append(value)

        return result

    def visit_simple_name(self, node: Node, visited_children: List[Any]) -> str:
        """Process a simple name."""
        return node.text

    def generic_visit(self, node: Node, visited_children: List[Any]) -> Any:
        """Default handler."""
        return visited_children or node.text


def parse_filter(expr: str) -> Callable[[dict], bool]:
    """
    Parse a filter expression into a callable predicate.

    Args:
        expr: The filter expression (e.g., "age > 25 AND city = 'NYC'")

    Returns:
        A callable that takes a dict and returns bool

    Examples:
        >>> predicate = parse_filter("age > 25")
        >>> predicate({"age": 30})
        True
        >>> predicate({"age": 20})
        False
    """
    # Remove extra whitespace but preserve spaces in operators
    clean_expr = " ".join(expr.split())

    if not clean_expr:
        raise ValueError("Empty filter expression")

    tree = FILTER_GRAMMAR.parse(clean_expr)
    visitor = FilterVisitor()
    return visitor.visit(tree)
