from typing import Any
from pydantic import BaseModel

import json
import pytest

@pytest.fixture(scope="function") 
def test_A() -> dict[str, Any]:
    with open("tests/A.json", "r") as f:
        return json.load(f)

@pytest.fixture(scope="function")
def test_B() -> dict[str, Any]:
    with open("tests/B.json", "r") as f:
        return json.load(f)

def _simple_nested_list() -> list[dict[str, Any]]:
    return [
        {"patient": {"id": "abc123", "active": True}},
        {"patient": {"id": "def456", "active": True}},
        {"patient": {"id": "ghi789", "active": False}},
    ]


def _deep_nested_list() -> list[dict[str, Any]]:
    return [
        {
            "patient": {
                "id": "abc123",
                "active": True,
                "ints": [1, 2, 3],
                "some_dict": {"char": "a", "inner": {"msg": "A!"}},
                "list_of_dicts": [
                    {"num": 1, "text": "one", "inner": {"msg": "One!"}},
                    {"num": 2, "text": "two", "inner": {"msg": "Two!"}},
                ],
            }
        },
        {
            "patient": {
                "id": "def456",
                "active": False,
                "ints": [4, 5, 6],
                "some_dict": {"char": "b", "inner": {"msg": "B!"}},
                "list_of_dicts": [
                    {"num": 3, "text": "three", "inner": {"msg": "Three!"}},
                    {"num": 4, "text": "four", "inner": {"msg": "Four!"}},
                ],
            }
        },
        {
            "patient": {
                "id": "ghi789",
                "active": True,
                "ints": [7, 8, 9],
                "some_dict": {"char": "c", "inner": {"msg": "C!"}},
                "list_of_dicts": [
                    {"num": 5, "text": "five", "inner": {"msg": "Five!"}},
                    {"num": 6, "text": "six", "inner": {"msg": "Six!"}},
                ],
            }
        },
        {
            "patient": {
                "id": "jkl101112",
                "active": True,
                # 'ints' is deliberately missing
                "some_dict": {"char": "d", "inner": {"msg": "D!"}},
                # `list_of_dicts` is deliberately len=1 instead of len=2
                "list_of_dicts": [{"num": 7, "text": "seven", "inner": {"msg": "Seven!"}}],
            }
        },
    ]


@pytest.fixture(scope="function")
def simple_nested_list() -> list[dict[str, Any]]:
    return _simple_nested_list()


@pytest.fixture(scope="function") 
def deep_nested_list() -> list[dict[str, Any]]:
    return _deep_nested_list()


@pytest.fixture(scope="function")
def list_data() -> list[Any]:
    return _simple_nested_list()


@pytest.fixture(scope="function")
def simple_data() -> dict[str, Any]:
    return {
        "data": {"patient": {"id": "abc123", "active": True}},
        "list_data": _simple_nested_list(),
    }


@pytest.fixture(scope="function")
def nested_data() -> dict[str, Any]:
    return {"data": _deep_nested_list()}
