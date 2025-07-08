from typing import Any, Callable, Union

from chidian_rs import get  # type: ignore[attr-defined]

"""
A `Piper` class for independent dict-to-dict transformations.

The Piper class performs pure data transformations without schema validation.
It takes either a dictionary mapping or a callable function and applies it to input data.
"""


class Piper:
    def __init__(
        self, mapping: Union[dict[str, Any], Callable[[dict[str, Any]], dict[str, Any]]]
    ):
        """
        Initialize a Piper for dict-to-dict transformations.

        Args:
            mapping: Either a dictionary mapping {"target_field": "source_path"}
                    or a callable function that transforms dict -> dict
        """
        if not (isinstance(mapping, dict) or callable(mapping)):
            raise TypeError(
                f"Mapping must be dict or callable, got {type(mapping).__name__}"
            )

        self.mapping = mapping

    def forward(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply the transformation to input data."""
        if callable(self.mapping):
            return self._apply_callable_mapping(data)
        else:
            return self._apply_dict_mapping(data)

    def _apply_callable_mapping(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply callable mapping to data."""
        # Type assertion for mypy
        assert callable(self.mapping)
        return self.mapping(data)  # type: ignore

    def _apply_dict_mapping(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply dictionary mapping to data."""
        result = {}

        # Type assertion for mypy
        assert isinstance(self.mapping, dict)
        for target_field, mapping_spec in self.mapping.items():
            if isinstance(mapping_spec, str):
                # Simple path mapping
                result[target_field] = get(data, mapping_spec)
            elif callable(mapping_spec):
                # Callable mapping (lambda, partial, etc.)
                result[target_field] = mapping_spec(data)
            else:
                # Direct value
                result[target_field] = mapping_spec

        return result

    def __call__(self, data: dict[str, Any]) -> dict[str, Any]:
        """Make Piper callable."""
        return self.forward(data)
