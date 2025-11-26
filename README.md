# chidian

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Dict-to-dict data mappings that look like dicts

**chidian** lets you write data transformations as plain dictionaries. Your mapping *looks like* your output.

## Quick Start

```python
from chidian import mapper, grab

@mapper
def patient_summary(d):
    return {
        "patient_id": grab(d, "data.patient.id"),
        "is_active": grab(d, "data.patient.active"),
        "latest_visit": grab(d, "data.visits[0].date"),
    }

source = {
    "data": {
        "patient": {"id": "p-123", "active": True},
        "visits": [
            {"date": "2024-01-15", "type": "checkup"},
            {"date": "2024-02-20", "type": "followup"}
        ]
    }
}

result = patient_summary(source)
# {"patient_id": "p-123", "is_active": True, "latest_visit": "2024-01-15"}
```

## Core Idea

Write your mapping as the dict you want back:

```python
from chidian import mapper, grab, DROP, KEEP

@mapper
def normalize_user(d):
    return {
        # Static values — just write them
        "version": "2.0",

        # Pull from source
        "name": grab(d, "user.name"),

        # Nested output — nest your mapping
        "address": {
            "city": grab(d, "location.city"),
            "zip": grab(d, "location.postal"),
        },

        # Conditionally drop
        "risky_field": DROP.THIS_OBJECT if not grab(d, "verified") else grab(d, "data"),
    }
```

Decorated functions are shareable, testable, and composable:

```python
# Import and use directly
from myproject.mappings import normalize_user, patient_summary

# Chain mappings
result = patient_summary(normalize_user(raw_data))
```

## `grab(data, path)`

Extract values using dot notation and bracket indexing:

```python
grab(d, "user.name")           # Nested access
grab(d, "items[0]")            # List index
grab(d, "items[-1]")           # Negative index
grab(d, "users[*].name")       # Map over list
```

## `DROP` — Conditional Removal

Control what gets excluded from output. `DROP` propagates upward through the structure:

| Sentinel | Effect |
|----------|--------|
| `DROP.THIS_OBJECT` | Remove this value (or list item, or dict) |
| `DROP.PARENT` | Remove the parent container |
| `DROP.GRANDPARENT` | Remove two levels up |
| `DROP.GREATGRANDPARENT` | Remove three levels up (raises if out of bounds) |

```python
@mapper
def with_drops(d):
    return {
        "kept": {"id": grab(d, "data.patient.id")},
        "dropped": {
            "trigger": DROP.THIS_OBJECT,  # This whole dict removed
            "ignored": "never appears",
        },
        "items": [
            {"bad": DROP.PARENT, "also_ignored": "x"},  # Removes entire list
            {"good": "value"},
        ],
    }

# Result: {"kept": {"id": "..."}}
```

**In lists**, `DROP.THIS_OBJECT` removes just that item:

```python
@mapper
def filter_list(d):
    return {
        "tags": [
            "first_kept",
            DROP.THIS_OBJECT,  # Removed
            "third_kept",
            {"nested": DROP.THIS_OBJECT},  # Entire dict removed
        ],
    }

# Result: {"tags": ["first_kept", "third_kept"]}
```

## `KEEP` — Preserve Empty Values

By default, empty values (`{}`, `[]`, `""`, `None`) are removed. Wrap with `KEEP()` to preserve them:

```python
from chidian import KEEP

@mapper
def with_empties(d):
    return {
        "explicit_empty": KEEP({}),      # Preserved as {}
        "explicit_none": KEEP(None),     # Preserved as None
        "implicit_empty": {},            # Removed by default
        "normal_value": "hello",
    }

# Result: {"explicit_empty": {}, "explicit_none": None, "normal_value": "hello"}
```

## Decorator Options

```python
@mapper(remove_empty=False)
def keep_all_empties(d):
    return {
        "empty_dict": {},   # Kept
        "empty_list": [],   # Kept
        "none_val": None,   # Kept
    }
```

## Strict Mode

Catch missing keys during development:

```python
from chidian import mapper, grab, mapping_context

@mapper
def risky_mapping(d):
    return {
        "id": grab(d, "data.patient.id"),
        "missing": grab(d, "key.not.found"),  # Doesn't exist
    }

# Normal — missing keys become empty/removed
result = risky_mapping(source)

# Strict — raises KeyError on missing keys
with mapping_context(strict=True):
    risky_mapping(source)  # KeyError!
```

**Note**: Strict mode distinguishes between "key not found" and "key exists with `None` value":

```python
source = {"has_none": None}

@mapper
def check_none(d):
    return {
        "explicit_none": grab(d, "has_none"),      # OK — key exists, value is None
        "missing": grab(d, "does.not.exist"),      # Raises in strict mode
    }
```

## Validation

chidian includes a dict-like validation DSL that mirrors your data structure:

```python
from chidian.validation import Required, Optional, validate, to_pydantic, Gte, InSet

schema = {
    "name": Required(str),
    "email": Optional(str),
    "age": int & Gte(0),
    "role": InSet({"admin", "user"}),
    "tags": [str],
    "profile": {
        "bio": Optional(str),
        "avatar_url": str,
    },
}

# Validate data
data = {"name": "Alice", "age": 30, "role": "admin", "tags": ["python"]}
result = validate(data, schema)

if result.is_ok():
    print("Valid!", result.value)
else:
    for path, msg in result.error:
        print(f"  {'.'.join(map(str, path))}: {msg}")
```

### Composing Validators

Use `&` (and) and `|` (or) to combine validators:

```python
from chidian.validation import IsType, Gt, Matches

# Both must pass
positive_int = IsType(int) & Gt(0)

# Either can pass
str_or_int = str | int

# With regex
email = str & Matches(r"^[\w.-]+@[\w.-]+\.\w+$")
```

### Pydantic Integration

Compile schemas to Pydantic models for runtime validation:

```python
User = to_pydantic("User", {
    "name": Required(str),
    "email": Optional(str),
    "age": int,
})

user = User(name="Alice", age=30)  # Full Pydantic validation
```

### Built-in Validators

| Validator | Description |
|-----------|-------------|
| `Required(v)` | Field cannot be None |
| `Optional(v)` | Field can be None |
| `IsType(t)` | Value must be instance of type |
| `InRange(lo, hi)` | Length must be in range |
| `InSet(values)` | Value must be in set |
| `Matches(pattern)` | String must match regex |
| `Gt`, `Gte`, `Lt`, `Lte` | Numeric comparisons |
| `Between(lo, hi)` | Value between bounds |
| `Predicate(fn, msg)` | Custom validation function |

## API Reference

### `@mapper` / `@mapper(remove_empty=True)`

Decorator that transforms a mapping function into a callable mapper.

### `grab(data, path)`

Extract values using dot notation and bracket indexing:

```python
grab(d, "user.name")           # Nested access
grab(d, "items[0]")            # List index
grab(d, "items[-1]")           # Negative index
grab(d, "users[*].name")       # Map over list
```

## Design Philosophy

Built by data engineers, for data engineers. chidian solves common pain points:

**Challenges:**
- Verbose edge-case handling
- Hard to share one-off code
- Difficult collaboration on data transformations

**Solutions:**
- **Iterate over perfection**: Learn and adapt as you build
- **Functions as first-class objects**: Compose transformations cleanly
- **Keep things dict-like**: Simple, universal structure that's quick to read

chidian applies functional programming principles to data mappings, drawing inspiration from [Pydantic](https://github.com/pydantic/pydantic), [JMESPath](https://github.com/jmespath), [funcy](https://github.com/Suor/funcy), and others.

## Contributing

Contributions welcome! Open an issue to discuss your idea before submitting a PR.

---

See [tests](/tests) for more examples.
