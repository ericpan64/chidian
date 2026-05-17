"""Tokenizer for chidian path DSL."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class TokenKind(Enum):
    NAME = auto()
    NUMBER = auto()
    DOT = auto()
    LBRACK = auto()
    RBRACK = auto()
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    COLON = auto()
    STAR = auto()
    MINUS = auto()


@dataclass(frozen=True)
class Token:
    kind: TokenKind
    value: str
    pos: int


_TOKEN_RE = re.compile(
    r"(?P<NAME>[A-Za-z_][A-Za-z0-9_-]*)"
    r"|(?P<NUMBER>[0-9]+)"
    r"|(?P<DOT>\.)"
    r"|(?P<LBRACK>\[)"
    r"|(?P<RBRACK>\])"
    r"|(?P<LPAREN>\()"
    r"|(?P<RPAREN>\))"
    r"|(?P<COMMA>,)"
    r"|(?P<COLON>:)"
    r"|(?P<STAR>\*)"
    r"|(?P<MINUS>-)"
    r"|(?P<WS>\s+)"
)

_KIND_BY_GROUP = {
    "NAME": TokenKind.NAME,
    "NUMBER": TokenKind.NUMBER,
    "DOT": TokenKind.DOT,
    "LBRACK": TokenKind.LBRACK,
    "RBRACK": TokenKind.RBRACK,
    "LPAREN": TokenKind.LPAREN,
    "RPAREN": TokenKind.RPAREN,
    "COMMA": TokenKind.COMMA,
    "COLON": TokenKind.COLON,
    "STAR": TokenKind.STAR,
    "MINUS": TokenKind.MINUS,
}


def tokenize(s: str) -> list[Token]:
    """Tokenize a path string. Whitespace is skipped. Raises ValueError on unknown chars."""
    tokens: list[Token] = []
    pos = 0
    n = len(s)
    while pos < n:
        m = _TOKEN_RE.match(s, pos)
        if m is None:
            raise ValueError(f"unexpected character {s[pos]!r} at position {pos}")
        group = m.lastgroup
        assert group is not None
        if group != "WS":
            tokens.append(Token(_KIND_BY_GROUP[group], m.group(), pos))
        pos = m.end()
    return tokens
