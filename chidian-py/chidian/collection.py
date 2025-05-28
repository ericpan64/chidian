from typing import Any

# import pyarrow as pa

"""
A `DataCollection` is a collection of `dict[str, Any]` objects that can be either:
1. A group of related dictionaries (formerly DictGroup)
2. A shard of data not directly associated to a specific Pydantic model (formerly DataShard)

It provides a convenient DSL for querying the collection and doing cross-collection references/relationships.

It is a subclass of `dict` and can be used as a dictionary.

It can be exported to a `QueryableTable` for use with PyArrow (this will create a table where each key across all dicts will become a column)
"""
class DataCollection(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_shard = kwargs.get('is_shard', False)
    
    def get(self, key: str, default: Any = None) -> Any:
        ...
    
    def select(self, key: str) -> "DataCollection":
        """
        Selects a subset of the collection based on the key
        """
        ...

    def to_json(self) -> str:
        """
        Converts the collection to a JSON string
        """
        ...
    
    @property
    def is_shard(self) -> bool:
        """
        Returns True if this is a data shard (not associated to a specific Pydantic model)
        """
        return self._is_shard
    
    # def to_table(self) -> pa.Table:
    #     """
    #     Converts the collection to a PyArrow table. Assumes all unique key paths are columns
    #     """
    #     ...

    ...