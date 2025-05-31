from typing import Any, Optional, TypeVar, Generic, Type, Tuple
from .recordset import RecordSet
from .lib import put

"""Bidirectional, lossless transformation between Pydantic models."""

SourceT = TypeVar('SourceT')
TargetT = TypeVar('TargetT')


class Lens(Generic[SourceT, TargetT]):
    """Bidirectional, lossless transformation between Pydantic models."""
    
    def __init__(
        self,
        source_model: Type[SourceT],
        target_model: Type[TargetT],
        mappings: dict[str, str],
        strict: bool = True
    ):
        """Initialize a bidirectional lens between Pydantic models."""
        # Validate Pydantic models
        for model, name in [(source_model, "source"), (target_model, "target")]:
            if not (hasattr(model, 'model_fields') or hasattr(model, '__fields__')):
                raise TypeError(f"{name}_model must be a Pydantic BaseModel")
        
        # Validate string-only mappings
        for source_path, target_path in mappings.items():
            if not isinstance(source_path, str) or not isinstance(target_path, str):
                raise TypeError("Lens only supports string path mappings")
        
        self.source_model = source_model
        self.target_model = target_model
        self.mappings = mappings
        self.strict = strict
        
        # Import get function
        from .chidian_rs import get as _get
        self._get = _get
        
        # Pre-compute reverse mappings
        self._reverse_mappings = {v: k for k, v in mappings.items()}
        
        # Validate reversibility
        if strict and not self.can_reverse():
            duplicates = [v for v in mappings.values() if list(mappings.values()).count(v) > 1]
            raise ValueError(f"Lens is not reversible - duplicate target paths: {duplicates}")
    
    def forward(self, source: SourceT) -> Tuple[TargetT, RecordSet]:
        """Transform source model to target model + spillover."""
        # Convert to dict
        source_dict = source.model_dump() if hasattr(source, 'model_dump') else source.dict()
        
        # Apply mappings
        target_data = {}
        mapped_paths = set()
        
        for source_path, target_path in self.mappings.items():
            value = self._get(source_dict, source_path)
            if value is not None:
                target_data = put(target_data, target_path, value, strict=False)
                mapped_paths.add(source_path)
        
        # Create target and spillover
        target = self.target_model.model_validate(target_data)
        spillover_data = self._collect_spillover(source_dict, mapped_paths)
        spillover = RecordSet([spillover_data]) if spillover_data else RecordSet()
        
        return target, spillover
    
    def reverse(self, target: TargetT, spillover: RecordSet) -> SourceT:
        """Transform target model + spillover back to source model (lossless)."""
        if not self.can_reverse():
            raise ValueError("This lens cannot reverse - mappings are not bidirectional")
        
        # Convert target to dict
        target_dict = target.model_dump() if hasattr(target, 'model_dump') else target.dict()
        
        # Apply reverse mappings
        source_data = {}
        for target_path, source_path in self._reverse_mappings.items():
            value = self._get(target_dict, target_path)
            if value is not None:
                source_data = put(source_data, source_path, value, strict=False)
        
        # Merge spillover
        if spillover and spillover._items:
            source_data = {**spillover._items[0], **source_data}
        
        return self.source_model.model_validate(source_data)
    
    def can_reverse(self) -> bool:
        """Check if this lens can perform reverse transformations."""
        target_paths = list(self.mappings.values())
        return len(target_paths) == len(set(target_paths))
    
    def _collect_spillover(self, source_dict: dict, mapped_paths: set[str]) -> dict[str, Any]:
        """Collect data from source that wasn't mapped to target."""
        spillover = {}
        
        def _extract_unmapped(obj: Any, path: str = "") -> None:
            nonlocal spillover
            if isinstance(obj, dict):
                for key, value in obj.items():
                    field_path = f"{path}.{key}" if path else key
                    
                    # Check if this exact path was mapped
                    if field_path not in mapped_paths:
                        # Check if any parent path was mapped
                        is_covered = any(
                            field_path.startswith(mapped_path + ".") or 
                            field_path.startswith(mapped_path + "[")
                            for mapped_path in mapped_paths
                        )
                        
                        if not is_covered:
                            spillover = put(spillover, field_path, value, strict=False)
                        else:
                            # Recurse into nested structures
                            _extract_unmapped(value, field_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    item_path = f"{path}[{i}]"
                    _extract_unmapped(item, item_path)
        
        _extract_unmapped(source_dict)
        return spillover