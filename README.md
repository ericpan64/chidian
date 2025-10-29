# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Declarative, type-safe data mapping for savvy data engineers

**chidian** is a composable framework for building readable data transformations with **Pydantic v2**.

## Quick Start
```python
from pydantic import BaseModel
from chidian import Mapper
import chidian.partials as p

# Source data (nested)
source_data = {
    "name": {"first": "Gandalf", "given": ["the", "Grey"], "suffix": None},
    "address": {
        "street": ["Bag End", "Hobbiton"],
        "city": "The Shire",
        "postal_code": "ME001",
        "country": "Middle Earth"
    }
}

# Target data (flat)
target = {
    "full_name": "Gandalf the Grey",
    "address": "Bag End\nHobbiton\nThe Shire\nME001\nMiddle Earth"
}

# Define schemas
class SourceSchema(BaseModel):
    name: dict
    address: dict

class TargetSchema(BaseModel):
    full_name: str
    address: str

# Create type-safe mapper
person_mapping = Mapper(
    {
        "full_name": p.get([
            "name.first",
            "name.given[*]",
            "name.suffix"
        ]).join(" ", flatten=True),

        "address": p.get([
            "address.street[*]",
            "address.city",
            "address.postal_code",
            "address.country"
        ]).join("\n", flatten=True),
    },
    min_input_schemas=[SourceSchema],
    output_schema=TargetSchema,
)

# Execute
result = person_mapping(SourceSchema(**source_data))
assert result == TargetSchema(**target)
```

## Core Features

| Component        | Purpose                                                                  |
| ---------------- | ------------------------------------------------------------------------ |
| **Mapper**       | Dict→dict transformations with optional schema validation                |
| **DataMapping**  | Pydantic-validated, type-safe transformations                            |
| **Partials API** | Composable operators for concise transformation chains                   |
| **Table**        | Sparse tables with path queries, joins, pandas/polars interop           |
| **Lexicon**      | Bidirectional code lookups (e.g., LOINC ↔ SNOMED) with metadata         |

## Table & DataFrames

Seamless conversion between chidian Tables and pandas/polars:

```bash
pip install 'chidian[pandas]'   # pandas support
pip install 'chidian[polars]'   # polars support
pip install 'chidian[df]'       # both
```

```python
from chidian.table import Table

table = Table([
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
])

df_pd = table.to_pandas(index=True)
df_pl = table.to_polars(add_index=True)
```

### Flatten Nested Data

Convert nested structures into flat, column-based tables:

```python
table = Table([
    {"user": {"name": "John", "prefs": ["email", "sms"]}, "id": 123},
    {"user": {"name": "Jane", "prefs": ["phone"]}, "id": 456}
])

# Flatten with intuitive path notation
flat = table.flatten()
print(flat.columns)
# {'id', 'user.name', 'user.prefs[0]', 'user.prefs[1]'}

# Export flattened data
table.to_pandas(flatten=True)
table.to_polars(flatten=True)
table.to_csv("flat.csv", flatten=True)

# Control flattening behavior
table.flatten(max_depth=2, array_index_limit=5)
```

**Features:**
- Path notation: `user.name`, `items[0]`, `data.settings.theme`
- Handles sparse data (different nesting per row)
- Special key escaping for dots/brackets
- Depth and array size controls

## Design Philosophy

Built by data engineers, for data engineers. chidian solves common pain points:

**Challenges:**
- Verbose edge-case handling
- Hard to share one-off code
- Difficult collaboration on data transformations

**Solutions:**
- **Iterate over perfection**: Learn and adapt as you build
- **Functions as first-class objects**: Compose transformations cleanly
- **JSON-first**: Simple, universal data structures

chidian applies functional programming principles to data mappings, drawing inspiration from [Pydantic](https://github.com/pydantic/pydantic), [JMESPath](https://github.com/jmespath), [funcy](https://github.com/Suor/funcy), and others.

## Contributing

Contributions welcome! Open an issue to discuss your idea before submitting a PR.

---

See [tests](/chidian/tests) for more examples.
