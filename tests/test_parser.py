"""Targeted tests for the hand-written path parser."""

from __future__ import annotations

import pytest

from chidian.lib.parser import Path, PathSegmentType, parse_path


def _kinds(path: Path) -> list[PathSegmentType]:
    return [s.type for s in path.segments]


def test_hyphenated_identifier():
    path = parse_path("a-b.c_1")
    assert _kinds(path) == [PathSegmentType.KEY, PathSegmentType.KEY]
    assert [s.value for s in path.segments] == ["a-b", "c_1"]


def test_whitespace_tolerance():
    a = parse_path("  a . b [ 0 ] ")
    b = parse_path("a.b[0]")
    assert _kinds(a) == _kinds(b)
    assert [s.value for s in a.segments] == [s.value for s in b.segments]


def test_negative_slice_bounds():
    path = parse_path("x[-3:-1]")
    assert _kinds(path) == [PathSegmentType.KEY, PathSegmentType.SLICE]
    assert path.segments[1].value == (-3, -1)


def test_slice_open_bounds():
    assert parse_path("x[:]").segments[-1].value == (None, None)
    assert parse_path("x[1:]").segments[-1].value == (1, None)
    assert parse_path("x[:5]").segments[-1].value == (None, 5)


def test_leading_bracket():
    path = parse_path("[0].patient")
    assert _kinds(path) == [PathSegmentType.INDEX, PathSegmentType.KEY]


def test_leading_wildcard():
    path = parse_path("[*].patient")
    assert _kinds(path) == [PathSegmentType.WILDCARD, PathSegmentType.KEY]


def test_tuple_basic():
    path = parse_path("(a, b.c)")
    assert len(path.segments) == 1
    seg = path.segments[0]
    assert seg.type is PathSegmentType.TUPLE
    inner = seg.value
    assert isinstance(inner, list) and len(inner) == 2
    assert [s.value for s in inner[0].segments] == ["a"]
    assert [s.value for s in inner[1].segments] == ["b", "c"]


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "a..b",
        "a[",
        "a[1",
        "(a,",
        "a.",
        "[",
        "a[]",
    ],
)
def test_malformed_raises(bad: str):
    with pytest.raises(ValueError):
        parse_path(bad)


def test_lru_cache_hits():
    parse_path.cache_clear()
    parse_path("foo.bar")
    parse_path("foo.bar")
    info = parse_path.cache_info()
    assert info.hits >= 1
