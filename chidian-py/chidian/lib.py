from typing import Any, Iterable

from pydantic import BaseModel

from .seeds import ApplyFunc

"""
`put` is a pure function that re-combines a combination of dicts or `DataCollection`s into a Pydantic model

(IDEA: it's the inverse of `get`, allows re-composing data into structs, and assumes that string key name will match)
"""
def put(data: dict[str, Any], model: type[BaseModel]) -> BaseModel:
    ...