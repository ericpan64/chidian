from typing import Any, Callable

"""
A `Mapper` class for independent dict-to-dict transformations.

The Mapper class performs pure data transformations without schema validation.
It takes a dictionary mapping where keys are target fields and values are
transformations to apply to the source data.
"""


class Mapper:
    def __init__(self, mapping: dict[str, Callable[[dict], Any] | Any]):
        """
        Initialize a Mapper for dict-to-dict transformations.

        Args:
            mapping: A dictionary mapping where:
                    - Keys are target field names
                    - Values can be:
                        - Callable transformations (e.g., lambda, partials, p.get)
                        - Direct values (strings, numbers, etc.)
        """
        if not isinstance(mapping, dict):
            raise TypeError(f"Mapping must be dict, got {type(mapping).__name__}")

        self.mapping = mapping

    def forward(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply the transformation to input data."""
        return self._apply_dict_mapping(data)

    def _apply_dict_mapping(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply dictionary mapping to data."""
        result = {}

        for target_field, mapping_spec in self.mapping.items():
            if callable(mapping_spec):
                # Callable mapping (lambda, partial, etc.)
                result[target_field] = mapping_spec(data)
            else:
                # Direct value (including strings)
                result[target_field] = mapping_spec

        return result

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Make Mapper callable."""
        return self.forward(data)
