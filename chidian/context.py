"""
Context manager for mapping configuration (e.g., strict mode).
"""

from contextlib import contextmanager
from contextvars import ContextVar

# Context variable for strict mode
_strict_mode: ContextVar[bool] = ContextVar("strict_mode", default=False)


def is_strict() -> bool:
    """Check if strict mode is currently enabled."""
    return _strict_mode.get()


@contextmanager
def mapping_context(*, strict: bool = False):
    """
    Context manager for mapping configuration.

    Args:
        strict: If True, grab() raises ValueError on missing keys instead of
               returning None. Distinguishes between "key not found" and
               "key exists with None value".

    Example:
        from chidian import mapper, grab, mapping_context

        @mapper
        def risky_mapping(d):
            return {
                "id": grab(d, "data.patient.id"),
                "missing": grab(d, "key.not.found"),  # Doesn't exist
            }

        # Normal — missing keys become None/removed
        result = risky_mapping(source)

        # Strict — raises ValueError on missing keys
        with mapping_context(strict=True):
            risky_mapping(source)  # ValueError!
    """
    token = _strict_mode.set(strict)
    try:
        yield
    finally:
        _strict_mode.reset(token)
