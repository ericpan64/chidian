"""
The `partials` module provides a set of standardized partial classes if you don't want to write a bunch of lambda function.

This makes it easier to standardize code and saves structure when exported to pure JSON.
"""

from typing import Any, Callable, Iterable, TypeVar, Union, List
import operator
from functools import partial, reduce

from .chidian import get as _get

T = TypeVar('T')


class FunctionChain:
    """Composable function chain that consolidates operations."""
    
    def __init__(self, *operations: Callable):
        self.operations = list(operations)
    
    def __rshift__(self, other: Union[Callable, 'FunctionChain', 'ChainableFn']) -> 'FunctionChain':
        """Chain operations with >> operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*self.operations, *other.operations)
        elif isinstance(other, ChainableFn):
            return FunctionChain(*self.operations, other.func)
        else:
            return FunctionChain(*self.operations, other)
    
    def __call__(self, value: Any) -> Any:
        """Apply all operations in sequence."""
        return reduce(lambda v, f: f(v), self.operations, value)
    
    def __repr__(self) -> str:
        ops = ' >> '.join(f.__name__ if hasattr(f, '__name__') else str(f) 
                          for f in self.operations)
        return f"FunctionChain({ops})"
    
    def __len__(self) -> int:
        """Number of operations in the chain."""
        return len(self.operations)


class ChainableFn:
    """Wrapper to make any function/partial chainable with >>."""
    
    def __init__(self, func: Callable):
        self.func = func
        # Preserve function metadata
        self.__name__ = getattr(func, '__name__', repr(func))
        self.__doc__ = getattr(func, '__doc__', None)
    
    def __rshift__(self, other: Union[Callable, FunctionChain, 'ChainableFn']) -> FunctionChain:
        """Start or extend a chain with >> operator."""
        if isinstance(other, FunctionChain):
            return FunctionChain(self.func, *other.operations)
        elif isinstance(other, ChainableFn):
            return FunctionChain(self.func, other.func)
        else:
            return FunctionChain(self.func, other)
    
    def __rrshift__(self, other: Union[Callable, FunctionChain]) -> FunctionChain:
        """Allow chaining when ChainableFn is on the right side."""
        if isinstance(other, FunctionChain):
            return FunctionChain(*other.operations, self.func)
        else:
            return FunctionChain(other, self.func)
    
    def __call__(self, *args, **kwargs):
        """Call the wrapped function."""
        return self.func(*args, **kwargs)
    
    def __repr__(self) -> str:
        return f"ChainableFn({self.__name__})"


def get(key: str, default: Any = None, apply: Any = None, strict: bool = False) -> Callable[[Any], Any]:
    """Create a partial function for get operations."""
    def get_partial(source):
        return _get(source, key, default=default, apply=apply, strict=strict)
    return get_partial


# Arithmetic operations using operator module
def add(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Add a value to the input."""
    if before:
        return partial(operator.add, value)
    else:
        return lambda x: operator.add(x, value)


def subtract(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Subtract a value from the input."""
    if before:
        return partial(operator.sub, value)
    else:
        return lambda x: operator.sub(x, value)


def multiply(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Multiply the input by a value."""
    if before:
        return partial(operator.mul, value)
    else:
        return lambda x: operator.mul(x, value)


def divide(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Divide the input by a value."""
    if before:
        return partial(operator.truediv, value)
    else:
        return lambda x: operator.truediv(x, value)


# Comparison operations using operator module
def equals(value: Any) -> Callable[[Any], bool]:
    """Check if input equals the given value."""
    return partial(operator.eq, value)


def not_equal(value: Any) -> Callable[[Any], bool]:
    """Check if input does not equal the given value."""
    return partial(operator.ne, value)


def equivalent(value: Any) -> Callable[[Any], bool]:
    """Check if input is the same object as the given value."""
    return partial(operator.is_, value)


def not_equivalent(value: Any) -> Callable[[Any], bool]:
    """Check if input is not the same object as the given value."""
    return partial(operator.is_not, value)


def contains(value: Any) -> Callable[[Any], bool]:
    """Check if input contains the given value."""
    return lambda x: operator.contains(x, value)


def not_contains(value: Any) -> Callable[[Any], bool]:
    """Check if input does not contain the given value."""
    return lambda x: not operator.contains(x, value)


def contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is contained in the given container."""
    return lambda x: operator.contains(container, x)


def not_contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is not contained in the given container."""
    return lambda x: not operator.contains(container, x)


def isinstance_of(type_or_types: type) -> Callable[[Any], bool]:
    """Check if input is an instance of the given type(s)."""
    return lambda x: isinstance(x, type_or_types)


# Iterable operations using operator module
def keep(n: int) -> Callable[[Iterable[T]], Iterable[T]]:
    """Keep only the first n items from an iterable."""
    return lambda x: x[:n]


def index(i: int) -> Callable[[Iterable[T]], T]:
    """Get the item at index i from an iterable."""
    return lambda x: operator.getitem(x, i)


# Standard library wrappers
def map_to_list(func: Callable[[T], Any]) -> Callable[[Iterable[T]], list]:
    """Apply a function to each item in an iterable and return a list."""
    return lambda iterable: list(map(func, iterable))


def filter_to_list(predicate: Callable[[T], bool]) -> Callable[[Iterable[T]], list]:
    """Filter an iterable using a predicate and return a list."""
    return lambda iterable: list(filter(predicate, iterable))


# String manipulation functions as ChainableFn
upper = ChainableFn(str.upper)
lower = ChainableFn(str.lower) 
strip = ChainableFn(str.strip)
capitalize = ChainableFn(str.capitalize)


def split(sep: str = None) -> ChainableFn:
    """Create a chainable split function."""
    return ChainableFn(partial(str.split, sep=sep))


def replace(old: str, new: str) -> ChainableFn:
    """Create a chainable replace function."""
    return ChainableFn(lambda s: s.replace(old, new))


def join(sep: str) -> ChainableFn:
    """Create a chainable join function."""
    return ChainableFn(lambda items: sep.join(items))


# Array/List operations as ChainableFn
first = ChainableFn(lambda x: x[0] if x else None)
last = ChainableFn(lambda x: x[-1] if x else None)
length = ChainableFn(len)


def at_index(i: int) -> ChainableFn:
    """Get element at index."""
    return ChainableFn(lambda x: x[i] if len(x) > i else None)


def slice_range(start: int = None, end: int = None) -> ChainableFn:
    """Slice a sequence."""
    return ChainableFn(lambda x: x[start:end])


# Type conversions as ChainableFn
to_int = ChainableFn(int)
to_float = ChainableFn(float)
to_str = ChainableFn(str)
to_bool = ChainableFn(bool)


# Common data transformations
def round_to(decimals: int) -> ChainableFn:
    """Round to specified decimals."""
    return ChainableFn(partial(round, ndigits=decimals))


def default_to(default_value: Any) -> ChainableFn:
    """Replace None with default value."""
    return ChainableFn(lambda x: default_value if x is None else x)


def extract_id() -> ChainableFn:
    """Extract ID from FHIR reference (e.g., 'Patient/123' -> '123')."""
    return ChainableFn(lambda ref: ref.split('/')[-1] if '/' in str(ref) else ref)


def format_string(template: str) -> ChainableFn:
    """Format value into a string template."""
    return ChainableFn(lambda x: template.format(x))