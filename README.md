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
