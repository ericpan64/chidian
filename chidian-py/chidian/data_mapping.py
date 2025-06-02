"""
Unified data mapping interface that supports both unidirectional (View) and bidirectional (Lens) transformations.
"""

from typing import Any, Callable, Optional, Tuple, Type, TypeVar

from pydantic import BaseModel

from .chidian_rs import get
from .lib import put
from .recordset import RecordSet

# Type variables for generic models
SourceT = TypeVar("SourceT", bound=BaseModel)
TargetT = TypeVar("TargetT", bound=BaseModel)


class DataMapping:
    """
    A unified data mapping interface for transformations between Pydantic models.

    Supports two modes:
    - View (unidirectional): Complex mappings with functions, conditions, etc.
    - Lens (bidirectional): Simple string-to-string path mappings that can be reversed
    """

    def __init__(
        self,
        source_model: Type[SourceT],
        target_model: Type[TargetT],
        mapping: dict[str, str] | dict[str, str | Callable] | Callable[[dict], dict],
        bidirectional: bool = False,
        strict: bool = True,
        metadata: Optional[dict] = None,
    ):
        """
        Initialize a data mapping between Pydantic models.

        Args:
            source_model: Source Pydantic BaseModel class
            target_model: Target Pydantic BaseModel class
            mapping: For bidirectional mode: dict of string-to-string path mappings.
                    For unidirectional mode: dict of field mappings (strings or callables)
                    or a callable that transforms source dict to target dict
            bidirectional: If True, enables bidirectional mode with reversible mappings
            strict: If True, validate against models and fail on errors
            metadata: Optional metadata about the mapping
        """
        self._validate_pydantic_models(source_model, target_model)

        self.source_model = source_model
        self.target_model = target_model
        self.mapping = mapping
        self.bidirectional = bidirectional
        self.strict = strict
        self.metadata = metadata or {}

        if self.bidirectional:
            self._setup_bidirectional_mapping(mapping, strict)
        else:
            self._setup_unidirectional_mapping(mapping)

    def forward(self, source: SourceT | dict) -> TargetT | Tuple[TargetT, RecordSet]:
        """
        Transform source model to target model.

        Args:
            source: Instance of source_model or dict

        Returns:
            - Unidirectional mode: Instance of target_model
            - Bidirectional mode: Tuple of (target_model, spillover RecordSet)
        """
        validated_source: SourceT = self._validate_and_convert_source(source)
        source_dict = self._convert_to_dict(validated_source)

        if self.bidirectional:
            return self._forward_bidirectional(source_dict)
        else:
            return self._forward_unidirectional(source_dict)

    def reverse(self, target: TargetT, spillover: Optional[RecordSet] = None) -> Any:
        """
        Reverse transformation (target to source). Only available in bidirectional mode.

        Args:
            target: Instance of target_model
            spillover: Optional spillover data from forward transformation

        Returns:
            Instance of source_model
        """
        if not self.bidirectional:
            raise RuntimeError("reverse() is only available in bidirectional mode")

        if not self.is_reversible():
            raise ValueError(
                "This mapping cannot reverse - mappings are not bidirectional"
            )

        # Convert target to dict
        target_dict = target.model_dump()

        # Apply reverse mappings
        source_data: dict[str, Any] = {}
        for target_path, source_path in self._reverse_mappings.items():
            value = get(target_dict, target_path)
            if value is not None:
                source_data = put(source_data, source_path, value, strict=False)

        # Merge spillover if provided
        if spillover and len(spillover) > 0:
            spillover_data = spillover._items[0]
            source_data = self._merge_dicts(source_data, spillover_data)

        # Create source model
        return self.source_model.model_validate(source_data)

    def is_reversible(self) -> bool:
        """Check if this mapping can be reversed (bidirectional mode only)."""
        if not self.bidirectional:
            return False

        # Check for duplicate target paths (many-to-one mappings)
        # Type guard to ensure mapping is dict for bidirectional mode
        if not isinstance(self.mapping, dict):
            return False
        target_paths = list(self.mapping.values())
        return len(target_paths) == len(set(target_paths))

    def can_reverse(self) -> bool:
        """Alias for is_reversible() for backward compatibility."""
        return self.is_reversible()

    def _validate_pydantic_models(self, source_model: Type, target_model: Type) -> None:
        """Validate that models are Pydantic v2 BaseModels."""
        if not hasattr(source_model, "model_fields"):
            raise TypeError(
                f"source_model must be a Pydantic v2 BaseModel, got {type(source_model)}"
            )
        if not hasattr(target_model, "model_fields"):
            raise TypeError(
                f"target_model must be a Pydantic v2 BaseModel, got {type(target_model)}"
            )

    def _setup_bidirectional_mapping(self, mapping: Any, strict: bool) -> None:
        """Setup and validate bidirectional mapping configuration."""
        self._validate_bidirectional_mapping_type(mapping)
        self._validate_bidirectional_mapping_paths(mapping)
        self._reverse_mappings = {v: k for k, v in mapping.items()}

        if strict:
            self._validate_mapping_reversibility(mapping)

    def _validate_bidirectional_mapping_type(self, mapping: Any) -> None:
        """Validate that bidirectional mapping is a dictionary."""
        if not isinstance(mapping, dict):
            raise TypeError(
                "Bidirectional mappings must be dict of string-to-string paths"
            )

    def _validate_bidirectional_mapping_paths(self, mapping: dict) -> None:
        """Validate that all bidirectional mappings are string-to-string."""
        for source_path, target_path in mapping.items():
            if not isinstance(source_path, str) or not isinstance(target_path, str):
                raise TypeError(
                    "Bidirectional mappings must be string-to-string paths. "
                    f"Got {type(source_path).__name__} -> {type(target_path).__name__}"
                )

    def _validate_mapping_reversibility(self, mapping: dict) -> None:
        """Validate that mapping can be reversed without conflicts."""
        if not self.is_reversible():
            duplicates = [
                v for v in mapping.values() if list(mapping.values()).count(v) > 1
            ]
            raise ValueError(
                f"Mapping is not reversible - duplicate target paths: {duplicates}"
            )

    def _setup_unidirectional_mapping(self, mapping: Any) -> None:
        """Setup and validate unidirectional mapping configuration."""
        if callable(mapping):
            self.mapping_fn = mapping
        elif isinstance(mapping, dict):
            self._validate_unidirectional_dict_mapping(mapping)
        else:
            raise TypeError("Mapping must be callable or dict for unidirectional mode")

    def _validate_unidirectional_dict_mapping(self, mapping: dict) -> None:
        """Validate unidirectional dictionary mapping in strict mode."""
        # Validate mapping value types
        for target_field, mapping_spec in mapping.items():
            if not isinstance(target_field, str):
                raise TypeError(
                    f"Target field names must be strings, got {type(target_field).__name__}"
                )

            if not (isinstance(mapping_spec, str) or callable(mapping_spec)):
                raise TypeError(
                    f"Mapping values must be strings or callables. "
                    f"Got {type(mapping_spec).__name__} for field '{target_field}'"
                )

        if self.strict:
            validation_issues = self._validate_mapping()
            if validation_issues["missing_required_fields"]:
                raise ValueError(
                    f"Missing required target fields in mapping: {validation_issues['missing_required_fields']}"
                )

    def _validate_and_convert_source(self, source: SourceT | dict) -> SourceT:
        """Validate and convert source input to proper model instance."""
        if not isinstance(source, self.source_model):
            if self.strict:
                raise TypeError(
                    f"Expected {self.source_model.__name__}, got {type(source).__name__}"
                )
            return self.source_model.model_validate(source)
        return source

    def _convert_to_dict(self, source: SourceT) -> dict:
        """Convert source model to dictionary for processing."""
        return source.model_dump() if hasattr(source, "model_dump") else source

    def _forward_bidirectional(self, source_dict: dict) -> Tuple[TargetT, RecordSet]:
        """Handle forward transformation in bidirectional mode."""
        target_data, mapped_paths = self._apply_bidirectional_mappings(source_dict)
        target = self.target_model.model_validate(target_data)
        spillover = self._create_spillover(source_dict, mapped_paths)
        return target, spillover

    def _apply_bidirectional_mappings(self, source_dict: dict) -> Tuple[dict, set[str]]:
        """Apply bidirectional path mappings to source data."""
        target_data: dict[str, Any] = {}
        mapped_paths = set()

        # Type guard to ensure mapping is a dict for bidirectional mode
        if not isinstance(self.mapping, dict):
            raise RuntimeError("Bidirectional mapping must be a dictionary")

        for source_path, target_path in self.mapping.items():
            if not isinstance(target_path, str):
                raise RuntimeError(
                    "Bidirectional mappings must have string target paths"
                )
            value = get(source_dict, source_path)
            if value is not None:
                target_data = put(target_data, target_path, value, strict=False)
                mapped_paths.add(source_path)

        return target_data, mapped_paths

    def _create_spillover(self, source_dict: dict, mapped_paths: set[str]) -> RecordSet:
        """Create spillover RecordSet from unmapped data."""
        spillover_data = self._collect_spillover(source_dict, mapped_paths)
        return RecordSet([spillover_data]) if spillover_data else RecordSet()

    def _forward_unidirectional(self, source_dict: dict) -> Any:
        """Handle forward transformation in unidirectional mode."""
        if hasattr(self, "mapping_fn"):
            return self._apply_function_mapping(source_dict)
        else:
            return self._apply_dict_mapping(source_dict)

    def _apply_function_mapping(self, source_dict: dict) -> Any:
        """Apply callable function mapping to source data."""
        try:
            result = self.mapping_fn(source_dict)
            return self.target_model.model_validate(result)
        except Exception as e:
            if self.strict:
                raise ValueError(f"Error in mapping function: {e}")
            return result

    def _apply_dict_mapping(self, source_dict: dict) -> Any:
        """Apply dictionary field mappings to source data."""
        result = self._process_field_mappings(source_dict)
        return self._validate_and_construct_target(result)

    def _process_field_mappings(self, source_dict: dict) -> dict:
        """Process individual field mappings from the mapping dictionary."""
        result = {}

        # Type guard to ensure mapping is a dict for field processing
        if not isinstance(self.mapping, dict):
            raise RuntimeError("Field mapping processing requires a dictionary mapping")

        for target_field, mapping_spec in self.mapping.items():
            try:
                result[target_field] = self._process_mapping(source_dict, mapping_spec)
            except Exception as e:
                if self.strict:
                    raise ValueError(f"Error mapping field '{target_field}': {e}")
        return result

    def _validate_and_construct_target(self, result: dict) -> Any:
        """Validate and construct target model from processed data."""
        try:
            return self.target_model.model_validate(result)
        except Exception as e:
            if self.strict:
                raise ValueError(
                    f"Failed to construct {self.target_model.__name__}: {e}"
                )
            # In non-strict mode, we still need to return TargetT, so attempt validation anyway
            return self.target_model.model_validate(result)

    # Core transformation helper methods

    def _process_mapping(self, source: dict, mapping_spec: Any) -> Any:
        """Process a single mapping specification (unidirectional mode)."""
        # String path - use get
        if isinstance(mapping_spec, str):
            return get(source, mapping_spec)

        # Callable (FunctionChain, ChainableFn, or other callables)
        elif hasattr(mapping_spec, "__call__"):
            # Check if it's a chainable function
            if hasattr(mapping_spec, "func"):
                return mapping_spec(source)
            # Regular callable
            else:
                return mapping_spec(source)

        # Dict with conditional logic (legacy support)
        elif isinstance(mapping_spec, dict):
            if "source" in mapping_spec:
                # Check condition if present
                if "condition" in mapping_spec:
                    if not mapping_spec["condition"](source):
                        return None

                # Get the value
                value = self._process_mapping(source, mapping_spec["source"])

                # Apply transform if present
                if "transform" in mapping_spec:
                    value = mapping_spec["transform"](value)

                return value
            else:
                # Nested mapping
                return {
                    k: self._process_mapping(source, v) for k, v in mapping_spec.items()
                }

        # SEED objects (they should have an evaluate method)
        elif hasattr(mapping_spec, "evaluate"):
            return mapping_spec.evaluate(source)

        # Direct value
        else:
            return mapping_spec

    def _collect_spillover(self, source_dict: dict, mapped_paths: set[str]) -> dict:
        """Collect unmapped fields for spillover (bidirectional mode)."""
        spillover: dict[str, Any] = {}

        def collect_unmapped(data: dict, path: str = "", target_dict=None):
            if target_dict is None:
                target_dict = spillover

            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key

                # Check if this exact path was mapped
                path_mapped = current_path in mapped_paths

                if not path_mapped:
                    if isinstance(value, dict):
                        # Add nested dict to spillover
                        target_dict[key] = {}
                        collect_unmapped(value, current_path, target_dict[key])
                        # Remove empty dicts
                        if not target_dict[key]:
                            del target_dict[key]
                    else:
                        target_dict[key] = value

        collect_unmapped(source_dict)
        return spillover

    def _merge_dicts(self, target: dict, source: dict) -> dict:
        """Deep merge two dictionaries."""
        result = target.copy()

        for key, value in source.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._merge_dicts(result[key], value)
            else:
                result[key] = value

        return result

    def _validate_mapping(self) -> dict[str, list[str]]:
        """Validate the mapping against source and target models (unidirectional mode with dict mapping)."""
        issues: dict[str, list[str]] = {
            "missing_required_fields": [],
            "unknown_target_fields": [],
            "invalid_source_fields": [],
        }

        # Skip validation for callable mappings
        if hasattr(self, "mapping_fn"):
            return issues

        # Type guard for dict mapping
        if not isinstance(self.mapping, dict):
            return issues

        # Get target model fields
        target_fields = self._get_model_fields(self.target_model)

        # Check for required fields
        required_fields = {
            name
            for name, field_info in target_fields.items()
            if self._is_field_required(field_info)
        }
        mapped_fields = set(self.mapping.keys())
        issues["missing_required_fields"] = list(required_fields - mapped_fields)

        # Check for unknown target fields
        all_target_fields = set(target_fields.keys())
        issues["unknown_target_fields"] = list(mapped_fields - all_target_fields)

        return issues

    def _get_model_fields(self, model: type) -> dict:
        """Get fields from Pydantic v2 model."""
        return getattr(model, "model_fields", {})

    def _is_field_required(self, field_info) -> bool:
        """Check if field is required in Pydantic v2."""
        return field_info.is_required()
