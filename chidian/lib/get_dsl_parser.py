"""
DSL parser using PEG grammar for chidian path expressions.
"""

from functools import lru_cache
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
        return [
            s for s in flatten_sequence(visited_children) if isinstance(s, PathSegment)
        ]

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
        # nested_expr children are returned as raw text; parse each one on its own
        paths = [
            parse_path_peg(child)
            for child in flatten_sequence(visited_children)
            if isinstance(child, str)
        ]
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

    def visit_quoted_key(
        self, node: Node, visited_children: Sequence[Any]
    ) -> PathSegment:
        """Handle quoted keys like '["@id"]' or "['a.b']" """
        # visited_children = [lbrack, string, rbrack]
        return PathSegment.key(visited_children[1])

    def visit_dq_string(self, node: Node, visited_children: Sequence[Any]) -> str:
        return node.text[1:-1]

    def visit_sq_string(self, node: Node, visited_children: Sequence[Any]) -> str:
        return node.text[1:-1]

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


def _strip_whitespace(path_str: str) -> str:
    """Remove whitespace outside of quoted keys."""
    result = []
    quote: str | None = None
    for ch in path_str:
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch.isspace():
            continue
        result.append(ch)
    return "".join(result)


@lru_cache(maxsize=1024)
def parse_path_peg(path_str: str) -> Path:
    """Parse a path string into a Path object using PEG grammar."""
    if not path_str:
        raise ValueError("Empty path")

    clean_path = _strip_whitespace(path_str)

    try:
        parsed_tree = GET_DSL_GRAMMAR.parse(clean_path)
        segments = GetDSLVisitor().visit(parsed_tree)
    except Exception as e:
        raise ValueError(f"Parse error: {e}") from e

    return Path(segments)
