
"""
A `DictPiper` 

As a Piper processes data, it will consume SEEDs and apply them to the data accordingly
"""

class DictPiper:
    def __init__(self, mapping_fn: Callable[[dict[str, Any]], dict[str, Any]]):
        ...

    def run(self, data: dict[str, Any]) -> dict[str, Any]:
        ...
    ...