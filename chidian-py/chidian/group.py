from typing import Any

# import pyarrow as pa

"""
A `DictGroup` is a group of `dict[str, Any]` objects that are related to each other.

It provides a convenient DSL for querying the group and doing cross-group references/relationships.

It is a subclass of `dict` and can be used as a dictionary.

It can be exported to a `QueryableTable` for use with PyArrow (this will create a table where each key across all dicts will become a column)
"""
class DictGroup(dict):

    def __init__(self, *args, **kwargs):
        ...
    
    def get(self, key: str, default: Any = None) -> Any:
        ...
    
    def select(self, key: str) -> "DictGroup":
        """
        Selects a subset of the group based on the key
        """
        ...

    def to_json(self) -> str:
        """
        Converts the group to a JSON string
        """
        ...
    
    # def to_table(self) -> pa.Table:
    #     """
    #     Converts the group to a PyArrow table. Assumes all unique key paths are columns
    #     """
    #     ...

    ...


class DataShard(dict):
    """
    A `DataShard` is a dict that contains data related to the `DictGroup` but not associated to a specific Pydantic model

    By marking it as a `DataShard`, we will infer which Pydantic model it is related to within the `DictGroup` and serialize all matching keys
    """
    ...