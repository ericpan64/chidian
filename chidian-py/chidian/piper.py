
from typing import TypeVar, Generic, Union, Tuple
from .data_mapping import DataMapping
from .recordset import RecordSet

"""
A `Piper` class that executes DataMapping transformations.

The Piper class is a runtime that executes DataMapping instances.
DataMapping defines WHAT to map, Piper defines HOW to execute it.

As a Piper processes data, it will consume SEEDs and apply them to the data accordingly.
Uses a two-pass approach: first mapping, then cleanup of SEED directives.
"""

# Type variables for generic typing
InputT = TypeVar('InputT')
OutputT = TypeVar('OutputT')


class Piper(Generic[InputT, OutputT]):
    def __init__(self, data_mapping: 'DataMapping'):
        """
        Initialize a Piper for executing DataMapping transformations.
        
        Args:
            data_mapping: A DataMapping instance that defines the transformation
        """        
        self.data_mapping = data_mapping
        
        # Set up type and mode information
        self.source_type = data_mapping.source_model
        self.target_type = data_mapping.target_model
        # Compatibility aliases
        self.input_type = self.source_type
        self.output_type = self.target_type
        self.strict = data_mapping.strict
        
        self._mode = "lens" if data_mapping.bidirectional else "view"

    def forward(self, data: InputT) -> Union[OutputT, Tuple[OutputT, 'RecordSet']]:
        """Apply forward transformation (alias for run)."""
        # Type validation in strict mode
        if self.strict and not isinstance(data, self.source_type):
            raise TypeError(f"Expected {self.source_type.__name__}, got {type(data).__name__}")

        return self.data_mapping.forward(data)
    
    def reverse(self, output_data: OutputT, spillover: 'RecordSet' = None) -> InputT:
        """Apply reverse transformation (only available for bidirectional DataMapping)."""
        if not self.data_mapping.bidirectional:
            raise ValueError("Reverse transformation only available for bidirectional mappings")

        return self.data_mapping.reverse(output_data, spillover or RecordSet())
    
    def can_reverse(self) -> bool:
        """Check if this piper supports reverse transformation."""
        return self.data_mapping.can_reverse()
    
    def __call__(self, data: InputT) -> Union[OutputT, Tuple[OutputT, 'RecordSet']]:
        """Make Piper callable."""
        return self.forward(data)