from typing import Any

"""
A `Mapper` is a class that converts between two objects of the same class or subclass.
"""
# Make this a Python protocol
class Mapper(dict):
    ...

"""
A `StringMapper` provides convenient two-way lookup of strings with the same semantic meaning
   For one-to-one mappings, lookup in both directions are supported. 
   For many-to-one / one-to-many mappings, the first value is taken as a default
    ```
    some_string_mapper = StringMapper({
        'a': 'b',
        ('c', 'd'): 'e',
    })
    some_string_mapper['a'] == 'b'
    some_string_mapper['b'] == 'a'
    some_string_mapper['c''] == 'e'
    some_string_mapper['e'] == 'c'   # default is 'c' since it comes first
    ```

   For one-to-many mappings, a default value is specified out of the possible options. E.g.
    ```
    some_string_mapper = StringMapper({
        'a': ('b', 'c'), # Default is 'b', since it comes first
    })
    some_string_mapper['a'] == 'b'   # default is 'b'
    some_string_mapper['b'] == 'a'
    some_string_mapper['c'] == 'a'
    ```

"""
class StringMapper(Mapper):
    def __call__(self, key: str | tuple) -> str | tuple:
        ...

"""
A `StructMapper` provides mapping between two Pydantic models in a single direction
"""
class StructMapper(Mapper):

    ...

# """
# A `BijectiveStructMapper` is a `StructMapper` that is bijective, i.e. it has a one-to-one mapping in both directions
# """
# class BijectiveStructMapper(StructMapper):

#     # Defines a `put` method and save state for reverse lookup
#     def put(...) -> ...:
#         ...
#     ...