"""
The `partials` module provides a set of standardized partial classes if you don't want to write a bunch of lambda function.

This makes it easier to standardize code and saves structure when exported to pure JSON.
"""

from typing import Any, Callable, Iterable, TypeVar, Union, List
import operator
from functools import partial, reduce

from .chidian_rs import get as _get

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
        # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
        return lambda x: operator.add(x, value)


def subtract(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Subtract a value from the input."""
    if before:
        return partial(operator.sub, value)
    else:
        # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
        return lambda x: operator.sub(x, value)


def multiply(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Multiply the input by a value."""
    if before:
        return partial(operator.mul, value)
    else:
        # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
        return lambda x: operator.mul(x, value)


def divide(value: Any, before: bool = False) -> Callable[[Any], Any]:
    """Divide the input by a value."""
    if before:
        return partial(operator.truediv, value)
    else:
        # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
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
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: operator.contains(x, value)


def not_contains(value: Any) -> Callable[[Any], bool]:
    """Check if input does not contain the given value."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: not operator.contains(x, value)


def contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is contained in the given container."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: operator.contains(container, x)


def not_contained_in(container: Any) -> Callable[[Any], bool]:
    """Check if input is not contained in the given container."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: not operator.contains(container, x)


def isinstance_of(type_or_types: type) -> Callable[[Any], bool]:
    """Check if input is an instance of the given type(s)."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: isinstance(x, type_or_types)


# Iterable operations using operator module
def keep(n: int) -> Callable[[Iterable[T]], Iterable[T]]:
    """Keep only the first n items from an iterable."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: x[:n]


def index(i: int) -> Callable[[Iterable[T]], T]:
    """Get the item at index i from an iterable."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda x: operator.getitem(x, i)


# Standard library wrappers
def map_to_list(func: Callable[[T], Any]) -> Callable[[Iterable[T]], list]:
    """Apply a function to each item in an iterable and return a list."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return lambda iterable: list(map(func, iterable))


def filter_to_list(predicate: Callable[[T], bool]) -> Callable[[Iterable[T]], list]:
    """Filter an iterable using a predicate and return a list."""
    # TODO: This shouldn't return a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
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
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda s: s.replace(old, new))


def join(sep: str) -> ChainableFn:
    """Create a chainable join function."""
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda items: sep.join(items))


# Array/List operations as ChainableFn
first = ChainableFn(lambda x: x[0] if x else None)
last = ChainableFn(lambda x: x[-1] if x else None)
length = ChainableFn(len)


def at_index(i: int) -> ChainableFn:
    """Get element at index."""
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda x: x[i] if len(x) > i else None)


def slice_range(start: int = None, end: int = None) -> ChainableFn:
    """Slice a sequence."""
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
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
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda x: default_value if x is None else x)


def extract_id() -> ChainableFn:
    """Extract ID from FHIR reference (e.g., 'Patient/123' -> '123')."""
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda ref: ref.split('/')[-1] if '/' in str(ref) else ref)


def format_string(template: str) -> ChainableFn:
    """Format value into a string template."""
    # TODO: This shouldn't use a lambda -- it needs to return a fixed point in memory (lambda gets recreated each time)
    return ChainableFn(lambda x: template.format(x))


# New partials replacing former SEED classes
def case(cases: dict[Any, Any] | list[tuple[Any, Any]], default: Any = None) -> ChainableFn:
    """Switch-like pattern matching for values with ordered evaluation.
    
    Args:
        cases: Dictionary or list of (condition, value) tuples
        default: Default value if no cases match
    
    Returns:
        ChainableFn that applies case matching to input value
    """
    def case_matcher(value):
        # Support both dict and list for ordered evaluation
        case_items = list(cases.items()) if isinstance(cases, dict) else cases
        
        for case_key, case_value in case_items:
            # Exact match
            if not callable(case_key) and value == case_key:
                return case_value
            
            # Function match
            if callable(case_key):
                try:
                    if case_key(value):
                        return case_value
                except (TypeError, AttributeError):
                    continue
        
        return default
    
    return ChainableFn(case_matcher)


def coalesce(*paths: str, default: Any = None) -> Callable[[Any], Any]:
    """Grab first non-empty value from multiple paths.
    
    Args:
        *paths: Paths to check in order
        default: Default value if all paths are empty/None
    
    Returns:
        Function that takes data and returns first non-empty value
    """
    def coalesce_func(data):
        for path in paths:
            value = _get(data, path)
            if value is not None and value != "":
                return value
        return default
    
    return coalesce_func


def template(template_str: str, skip_none: bool = False) -> Callable[..., str]:
    """Combine multiple values using a template string.
    
    Args:
        template_str: Template string with {} placeholders
        skip_none: If True, skip None values and adjust template
    
    Returns:
        Function that takes values and formats them into template
    """
    def template_formatter(*values):
        if skip_none:
            # Filter out None values
            filtered_values = [v for v in values if v is not None]
            # Create template with correct number of placeholders
            if filtered_values:
                adjusted_template = ' '.join('{}' for _ in filtered_values)
                return adjusted_template.format(*filtered_values)
            else:
                return ""
        else:
            return template_str.format(*values)
    
    return template_formatter


def flatten(paths: list[str], delimiter: str = ", ") -> Callable[[Any], str]:
    """Flatten values from multiple paths into a single delimited string.
    
    Args:
        paths: List of paths to extract values from
        delimiter: String to join values with
    
    Returns:
        Function that takes data and returns flattened string
    """
    def flatten_func(data):
        all_values = []
        for path in paths:
            values = _get(data, path)
            if isinstance(values, list):
                all_values.extend(str(v) for v in values if v is not None)
            elif values is not None:
                all_values.append(str(values))
        return delimiter.join(all_values)
    
    return flatten_func
