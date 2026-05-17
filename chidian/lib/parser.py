"""Path parser for chidian path expressions.

Hand-written recursive-descent parser. Output identical to the prior PEG
implementation: a ``Path`` of ``PathSegment``s consumed by ``traverse_path``.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from functools import lru_cache
from typing import List, Optional, Union

from .tokenizer import Token, TokenKind, tokenize


class PathSegmentType(Enum):
    KEY = auto()
    INDEX = auto()
    SLICE = auto()
    WILDCARD = auto()
    TUPLE = auto()


@dataclass
class PathSegment:
    type: PathSegmentType
    value: Union[str, int, tuple[Optional[int], Optional[int]], List["Path"]]

    @classmethod
    def key(cls, name: str) -> "PathSegment":
        return cls(PathSegmentType.KEY, name)

    @classmethod
    def index(cls, idx: int) -> "PathSegment":
        return cls(PathSegmentType.INDEX, idx)

    @classmethod
    def slice(cls, start: Optional[int], end: Optional[int]) -> "PathSegment":
        return cls(PathSegmentType.SLICE, (start, end))

    @classmethod
    def wildcard(cls) -> "PathSegment":
        return cls(PathSegmentType.WILDCARD, "*")

    @classmethod
    def tuple(cls, paths: List["Path"]) -> "PathSegment":
        return cls(PathSegmentType.TUPLE, paths)


@dataclass
class Path:
    segments: List[PathSegment]


class _Parser:
    """Recursive-descent parser over a token stream."""

    def __init__(self, tokens: list[Token], source: str) -> None:
        self.tokens = tokens
        self.source = source
        self.i = 0

    def _peek(self, offset: int = 0) -> Optional[Token]:
        idx = self.i + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def _eat(self, kind: TokenKind) -> Token:
        tok = self._peek()
        if tok is None or tok.kind is not kind:
            self._fail(f"expected {kind.name}")
        self.i += 1
        return tok  # type: ignore[return-value]

    def _fail(self, msg: str) -> None:
        tok = self._peek()
        if tok is None:
            raise ValueError(f"{msg} at end of input (source: {self.source!r})")
        raise ValueError(
            f"{msg} but got {tok.kind.name} {tok.value!r} at position {tok.pos} "
            f"(source: {self.source!r})"
        )

    # Grammar:
    # get_expr     = (array_access / key) (dot key)*
    # key          = (list_op / single / tuple)
    # array_access = single_index / multi_index
    # single       = name single_index?
    # list_op      = name? multi_index
    # tuple        = lparen nested_expr (comma nested_expr)* rparen
    # single_index = lbrack number rbrack
    # multi_index  = lbrack (star / slice) rbrack
    # slice        = number? colon number?

    def parse_get_expr(self) -> list[PathSegment]:
        segments: list[PathSegment] = []
        tok = self._peek()
        if tok is None:
            self._fail("empty path")
        assert tok is not None
        if tok.kind is TokenKind.LBRACK:
            segments.append(self._parse_array_access())
        else:
            segments.extend(self._parse_key())
        while True:
            tok = self._peek()
            if tok is None:
                break
            if tok.kind is not TokenKind.DOT:
                self._fail("expected '.'")
            self.i += 1
            segments.extend(self._parse_key())
        return segments

    def _parse_array_access(self) -> PathSegment:
        inner = self._peek(1)
        if inner is None:
            self._fail("unterminated '['")
            raise AssertionError
        if inner.kind is TokenKind.STAR or inner.kind is TokenKind.COLON:
            return self._parse_multi_index()
        if inner.kind is TokenKind.NUMBER or inner.kind is TokenKind.MINUS:
            # Disambiguate single_index vs slice by scanning for a COLON
            # before the matching RBRACK.
            j = self.i + 1
            while j < len(self.tokens):
                k = self.tokens[j].kind
                if k is TokenKind.RBRACK:
                    break
                if k is TokenKind.COLON:
                    return self._parse_multi_index()
                j += 1
            return self._parse_single_index()
        self._fail("expected number, '-', '*' or ':' after '['")
        raise AssertionError

    def _parse_key(self) -> list[PathSegment]:
        tok = self._peek()
        if tok is None:
            self._fail("expected key")
            raise AssertionError
        if tok.kind is TokenKind.LPAREN:
            return [self._parse_tuple()]
        if tok.kind is TokenKind.LBRACK:
            return [self._parse_array_access()]
        if tok.kind is TokenKind.NAME:
            self.i += 1
            nxt = self._peek()
            if nxt is not None and nxt.kind is TokenKind.LBRACK:
                bracket_seg = self._parse_array_access()
                return [PathSegment.key(tok.value), bracket_seg]
            return [PathSegment.key(tok.value)]
        self._fail("expected name, '[' or '('")
        raise AssertionError

    def _parse_tuple(self) -> PathSegment:
        self._eat(TokenKind.LPAREN)
        paths: list[Path] = [Path(self._parse_nested_expr())]
        while True:
            tok = self._peek()
            if tok is None:
                self._fail("unterminated tuple")
                raise AssertionError
            if tok.kind is TokenKind.COMMA:
                self.i += 1
                paths.append(Path(self._parse_nested_expr()))
                continue
            if tok.kind is TokenKind.RPAREN:
                self.i += 1
                return PathSegment.tuple(paths)
            self._fail("expected ',' or ')'")
            raise AssertionError

    def _parse_nested_expr(self) -> list[PathSegment]:
        segments = self._parse_key_no_tuple()
        while True:
            tok = self._peek()
            if tok is None or tok.kind is not TokenKind.DOT:
                break
            self.i += 1
            segments.extend(self._parse_key_no_tuple())
        return segments

    def _parse_key_no_tuple(self) -> list[PathSegment]:
        tok = self._peek()
        if tok is not None and tok.kind is TokenKind.LPAREN:
            raise ValueError(
                f"nested tuples not supported at position {tok.pos} "
                f"(source: {self.source!r})"
            )
        return self._parse_key()

    def _parse_single_index(self) -> PathSegment:
        self._eat(TokenKind.LBRACK)
        n = self._parse_signed_int()
        self._eat(TokenKind.RBRACK)
        return PathSegment.index(n)

    def _parse_multi_index(self) -> PathSegment:
        self._eat(TokenKind.LBRACK)
        tok = self._peek()
        if tok is None:
            self._fail("unterminated '['")
            raise AssertionError
        if tok.kind is TokenKind.STAR:
            self.i += 1
            self._eat(TokenKind.RBRACK)
            return PathSegment.wildcard()
        start: Optional[int] = None
        end: Optional[int] = None
        if tok.kind is TokenKind.NUMBER or tok.kind is TokenKind.MINUS:
            start = self._parse_signed_int()
        self._eat(TokenKind.COLON)
        nxt = self._peek()
        if nxt is not None and (
            nxt.kind is TokenKind.NUMBER or nxt.kind is TokenKind.MINUS
        ):
            end = self._parse_signed_int()
        self._eat(TokenKind.RBRACK)
        return PathSegment.slice(start, end)

    def _parse_signed_int(self) -> int:
        tok = self._peek()
        sign = 1
        if tok is not None and tok.kind is TokenKind.MINUS:
            sign = -1
            self.i += 1
            tok = self._peek()
        if tok is None or tok.kind is not TokenKind.NUMBER:
            self._fail("expected number")
            raise AssertionError
        self.i += 1
        return sign * int(tok.value)


@lru_cache(maxsize=4096)
def parse_path(path_str: str) -> Path:
    """Parse a chidian path expression into a ``Path``."""
    tokens = tokenize(path_str)
    parser = _Parser(tokens, path_str)
    segments = parser.parse_get_expr()
    if parser.i != len(tokens):
        leftover = tokens[parser.i]
        raise ValueError(
            f"unexpected trailing token {leftover.kind.name} {leftover.value!r} "
            f"at position {leftover.pos} (source: {path_str!r})"
        )
    return Path(segments)


__all__ = ["Path", "PathSegment", "PathSegmentType", "parse_path"]
