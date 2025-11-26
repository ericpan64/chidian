# chidian

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Dict-to-dict data mappings that look like dicts

**chidian** lets you write data transformations as plain dictionaries. Your mapping *looks like* your output.

## Quick Start

```python
from chidian import grab

source = {
    "data": {
        "patient": {"id": "p-123", "active": True},
        "visits": [
            {"date": "2024-01-15", "type": "checkup"},
            {"date": "2024-02-20", "type": "followup"}
        ]
    }
}

# Extract values using path notation
patient_id = grab(source, "data.patient.id")        # "p-123"
is_active = grab(source, "data.patient.active")     # True
latest_visit = grab(source, "data.visits[0].date")  # "2024-01-15"
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
from chidian import DROP, process_drops

data = {
    "kept": {"id": "123"},
    "dropped": {
        "trigger": DROP.THIS_OBJECT,  # This whole dict removed
        "ignored": "never appears",
    },
    "items": [
        {"bad": DROP.PARENT, "also_ignored": "x"},  # Removes entire list
        {"good": "value"},
    ],
}

result = process_drops(data)
# Result: {"kept": {"id": "123"}}
```

**In lists**, `DROP.THIS_OBJECT` removes just that item:

```python
from chidian import DROP, process_drops

data = {
    "tags": [
        "first_kept",
        DROP.THIS_OBJECT,  # Removed
        "third_kept",
        {"nested": DROP.THIS_OBJECT},  # Entire dict removed
    ],
}

result = process_drops(data)
# Result: {"tags": ["first_kept", "third_kept"]}
```

## `KEEP` — Preserve Empty Values

By default, empty values (`{}`, `[]`, `""`, `None`) are removed. Wrap with `KEEP()` to preserve them:

```python
from chidian import KEEP

# KEEP wraps a value to prevent automatic removal
data = {
    "explicit_empty": KEEP({}),      # Preserved as {}
    "explicit_none": KEEP(None),     # Preserved as None
    "implicit_empty": {},            # Will be removed by default
    "normal_value": "hello",
}
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

See [tests](/chidian/tests) for more examples.
