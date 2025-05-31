from typing import TypeVar, Generic, Type, Union, Callable, Tuple
from .view import View
from .lens import Lens
from .recordset import RecordSet

"""Type-safe data transformation pipeline."""

InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


class TypedPiper(Generic[InputT, OutputT]):
    """Type-safe data transformation pipeline."""
    
    def __init__(self, transformer: Union[View, Lens, Callable[[InputT], OutputT]]):
        self.transformer = transformer
        
        # Determine mode and inherit settings from transformer
        if isinstance(transformer, (View, Lens)):
            self.input_type = transformer.source_model
            self.output_type = transformer.target_model
            self.strict = transformer.strict
            self._mode = "lens" if isinstance(transformer, Lens) else "view"
        else:
            # Generic callable - minimal type safety
            self.input_type = None
            self.output_type = None
            self.strict = False
            self._mode = "callable"
    
    def forward(self, input_data: InputT) -> Union[OutputT, Tuple[OutputT, RecordSet]]:
        """Apply forward transformation."""
        # Type validation for strict mode
        if self.strict and self.input_type and not isinstance(input_data, self.input_type):
            raise TypeError(f"Expected {self.input_type.__name__}, got {type(input_data).__name__}")
        
        # Apply transformation
        if self._mode == "lens":
            return self.transformer.forward(input_data)
        elif self._mode == "view":
            return self.transformer.forward(input_data)
        else:
            return self.transformer(input_data)
    
    def reverse(self, output_data: OutputT, spillover: RecordSet = None) -> InputT:
        """Apply reverse transformation (only available for Lens)."""
        if self._mode != "lens":
            raise ValueError("Reverse transformation only available for Lens")
        
        return self.transformer.reverse(output_data, spillover or RecordSet())
    
    def can_reverse(self) -> bool:
        """Check if this piper supports reverse transformation."""
        return self._mode == "lens" and self.transformer.can_reverse()
    
    def __call__(self, input_data: InputT) -> Union[OutputT, Tuple[OutputT, RecordSet]]:
        """Allow TypedPiper to be called directly."""
        return self.forward(input_data)