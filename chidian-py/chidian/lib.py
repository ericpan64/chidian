from typing import Any, Iterable

from pydantic import BaseModel

from .seeds import ApplyFunc

"""
`get` is a pure function that provides a convenient DSL for grabbing data from a nested dictionary or list.
"""
def get(
    source: dict[str, Any] | list[Any],
    key: str,
    default: Any = None,
    apply: ApplyFunc | Iterable[ApplyFunc] | None = None,
    flatten: bool = False,
) -> Any:
    """
    Gets a value from the source dictionary using a `.` syntax.
    Handles None-checking (instead of raising error, returns default).

    `key` notes:
     - Use `.` to chain gets
     - Index and slice into lists, e.g. `[0]`, `[-1]`, `[:1]`, etc.
     - Iterate through a list using `[*]`
     - Get multiple items using `(firstKey,secondKey)` syntax (outputs as a tuple)
       The keys within the tuple can also be chained with `.`

    Optional param notes:
    - `default`: Return value if `key` results in a `None` (before other params apply)
    - `apply`: Use to safely chain operations on a successful get
    - `flatten`: Use to flatten the final result (e.g. nested lists)
    """
    ...

"""
`put` is a pure function that re-combines a combination of dicts or `DataCollection`s into a Pydantic model

(IDEA: it's the inverse of `get`, allows re-composing data into structs, and assumes that string key name will match)
"""
def put(data: dict[str, Any], model: type[BaseModel]) -> BaseModel:
    ...