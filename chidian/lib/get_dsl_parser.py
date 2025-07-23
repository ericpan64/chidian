"""
DSL parser using PEG grammar for chidian path expressions.
"""

from pathlib import Path as PathLib
from typing import Any, List, Sequence, Union

from parsimonious import Grammar, NodeVisitor
from parsimonious.nodes import Node

from .parser import Path, PathSegment

# Load the PEG grammar
GET_PEG_PATH = PathLib(__file__).parent / "dsl" / "get.peg"

with open(GET_PEG_PATH, "r") as f:
    GRAMMAR_TEXT = f.read()

GET_DSL_GRAMMAR = Grammar(GRAMMAR_TEXT)


GetDslTreeResults = Union[str, int, slice, tuple, List[Any]]


def flatten_sequence(seq: Sequence[Any]) -> List[Any]:
    """Flatten a nested sequence into a single list."""
    result = []
    for item in seq:
        if isinstance(item, (list, tuple)) and not isinstance(item, str):
            result.extend(flatten_sequence(item))
        else:
            result.append(item)
    return result


class GetDSLVisitor(NodeVisitor):
    """
    Generates tree structure for path parsing using PEG grammar.
    """

    def visit_get_expr(
        self, node: Node, visited_children: Sequence[Any]
    ) -> List[PathSegment]:
        """Entrypoint: handles full expression like 'a[0].b[*].c'"""
        segments = []

        # Collect all segments from the expression
        for child in visited_children:
            if child is None:
                continue
            elif isinstance(child, list):
                # Flatten lists of segments
                for item in child:
                    if isinstance(item, PathSegment):
                        segments.append(item)
                    elif isinstance(item, list):
                        segments.extend(s for s in item if isinstance(s, PathSegment))
            elif isinstance(child, PathSegment):
                segments.append(child)

        return segments

    def visit_key(
        self, node: Node, visited_children: Sequence[Any]
    ) -> Union[PathSegment, List[PathSegment]]:
        """Handle key which can be single, list_op, or tuple"""
        return visited_children[0]

    def visit_single(
        self, node: Node, visited_children: Sequence[Any]
    ) -> List[PathSegment]:
        """Handle single key expressions like 'a[0]'"""
        segments = []

        # visited_children: [name, single_index?]
        name = visited_children[0]
        if isinstance(name, PathSegment):
            segments.append(name)

        # Add index if present
        if len(visited_children) > 1 and visited_children[1] is not None:
            index_segment = visited_children[1]
            if isinstance(index_segment, PathSegment):
                segments.append(index_segment)

        return segments

    def visit_list_op(
        self, node: Node, visited_children: Sequence[Any]
    ) -> List[PathSegment]:
        """Handles expression meant to be applied on a list, e.g. `a[*]` or `[:1]`"""
        segments = []

        # visited_children: [name?, multi_index]
        name = visited_children[0]
        if name is not None and isinstance(name, PathSegment):
            segments.append(name)

        # Multi-index is always present
        multi_index = visited_children[1]
        if isinstance(multi_index, PathSegment):
            segments.append(multi_index)

        return segments

    def visit_tuple(self, node: Node, visited_children: Sequence[Any]) -> PathSegment:
        """Handle tuple expressions like '(a,b,c)'"""
        # Extract nested expressions from the tuple
        paths = []

        # Find all string expressions in the visited children
        for child in visited_children:
            if isinstance(child, str):
                path_segments = _parse_simple_path(child)
                paths.append(Path(path_segments))
            elif isinstance(child, list):
                # Handle comma-separated expressions
                for item in child:
                    if isinstance(item, str):
                        path_segments = _parse_simple_path(item)
                        paths.append(Path(path_segments))

        return PathSegment.tuple(paths)

    def visit_array_access(
        self, node: Node, visited_children: Sequence[Any]
    ) -> PathSegment:
        """Handle array access at the start of a path like '[0]' or '[*]'"""
        # visited_children[0] is either single_index or multi_index
        return visited_children[0]

    def visit_single_index(
        self, node: Node, visited_children: Sequence[Any]
    ) -> PathSegment:
        """Handle index expressions like '[0]'"""
        # visited_children = [lbrack, number, rbrack]
        return PathSegment.index(visited_children[1])

    def visit_multi_index(
        self, node: Node, visited_children: Sequence[Any]
    ) -> PathSegment:
        """Handles index expressions '[*]' and slices like '[1:]'"""
        # visited_children = [lbrack, (star | slice), rbrack]
        content = visited_children[1]
        if content == "*":
            return PathSegment.wildcard()
        elif isinstance(content, slice):
            return PathSegment.slice(content.start, content.stop)
        else:
            raise ValueError(f"Unexpected multi_index content: {content}")

    def visit_slice(self, node: Node, visited_children: Sequence[Any]) -> slice:
        """Handle slice notation like '[1:10]' or '[:]'"""
        # visited_children = [start?, colon, stop?]
        start = visited_children[0] if visited_children[0] is not None else None
        stop = visited_children[2] if visited_children[2] is not None else None
        return slice(start, stop)

    def visit_nested_expr(self, node: Node, visited_children: Sequence[Any]) -> str:
        """Handle nested expressions in tuples"""
        return node.text

    def visit_name(self, node: Node, visited_children: Sequence[Any]) -> PathSegment:
        """Handle identifiers like 'a', 'b', 'c'"""
        return PathSegment.key(node.text)

    def visit_number(self, node: Node, visited_children: Sequence[Any]) -> int:
        """Handle numbers like '0', '-1'"""
        return int(node.text)

    def visit_star(self, node: Node, visited_children: Sequence[Any]) -> str:
        """Handle wildcard '*'"""
        return "*"

    def generic_visit(
        self, node: Node, visited_children: Sequence[Any]
    ) -> Union[Sequence[Any], Any, None]:
        """Default handler for unspecified rules"""
        # Filter out None values and flatten
        filtered = [child for child in visited_children if child is not None]

        if len(filtered) > 1:
            return filtered
        elif len(filtered) == 1:
            return filtered[0]
        else:
            return None


def parse_path_peg(path_str: str) -> Path:
    """Parse a path string into a Path object using PEG grammar."""
    if not path_str:
        raise ValueError("Empty path")

    # Remove whitespace and parse
    clean_path = path_str.replace(" ", "")

    try:
        parsed_tree = GET_DSL_GRAMMAR.parse(clean_path)
        segments = GetDSLVisitor().visit(parsed_tree)

        if isinstance(segments, list):
            return Path(segments)
        else:
            return Path([segments])
    except Exception as e:
        raise ValueError(f"Parse error: {e}") from e


# For recursive parsing in tuples, avoid infinite recursion
def _parse_simple_path(path_str: str) -> List[PathSegment]:
    """Simple path parsing for use within tuples to avoid recursion."""
    if not path_str:
        return []

    # For tuple contents, use a simpler approach
    parts = path_str.split(".")
    segments = []

    for part in parts:
        # Check for array notation
        if "[" in part and "]" in part:
            # Extract key and index/slice
            key_part = part[: part.index("[")]
            bracket_part = part[part.index("[") : part.rindex("]") + 1]

            if key_part:
                segments.append(PathSegment.key(key_part))

            # Parse bracket content
            bracket_content = bracket_part[1:-1]  # Remove [ ]
            if bracket_content == "*":
                segments.append(PathSegment.wildcard())
            elif ":" in bracket_content:
                # Slice
                parts = bracket_content.split(":")
                start = int(parts[0]) if parts[0] else None
                end = int(parts[1]) if parts[1] else None
                segments.append(PathSegment.slice(start, end))
            else:
                # Index
                segments.append(PathSegment.index(int(bracket_content)))
        else:
            # Simple key
            segments.append(PathSegment.key(part))

    return segments
