from typing import Any

# import pyarrow as pa

"""
A `Group` is a group of `dict[str, Any]` objects that are related to each other.

It provides a convenient DSL for querying the group and doing cross-group references/relationships.

It is a subclass of `dict` and can be used as a dictionary.

It can be exported to a `QueryableTable` for use with PyArrow (this will create a table where each key across all dicts will become a column)
"""
class Group(dict):

    def __init__(self, *args, **kwargs):
        ...
    
    def get(self, key: str, default: Any = None) -> Any:
        ...
    ...

# class QueryableTable(pa.Table):
#     def select(self, columns: str | list[str]) -> "QueryableTable":
#         """
#         Allows for custom DSL
#         """
#         ...




class DataShard(dict):
    """
    A `DataShard` is a dict that contains data related to the group but not associated to a specific Pydantic model
    """
    ...