# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Declarative, type-safe data mapping for savvy data engineers

chidian is a pure Python framework for composable, readable, and sharable data mappings built on top of **Pydantic v2**.

## 30-second tour
```python
from pydantic import BaseModel
from chidian import Mapper
import chidian.partials as p

# 0. Identify the data you want to map
"""
Here we have this nested data:
"""
source_data = {
    "name": {
        "first": "Gandalf",
        "given": ["the", "Grey"],
        "suffix": None
    },
    "address": {
        "street": [
            "Bag End",
            "Hobbiton"
        ],
        "city": "The Shire",
        "postal_code": "ME001",
        "country": "Middle Earth"
    }
}
"""
And we want a flattened representation like:
"""
res = {
    "full_name": "Gandalf the Grey",
    "address": "Bag End\nHobbiton\nThe Shire\nME001\nMiddle Earth"
}

# 1. Define your source & target schemas
class SourceSchema(BaseModel):
    name: dict
    address: dict

class TargetSchema(BaseModel):
    full_name: str
    address: str

# 2. Create Mapper with transformations and schemas
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

# 3. Execute!
source_obj = SourceSchema(**source_data)
result = person_mapping(source_obj)
assert result == TargetSchema(**res)
```

See the [tests](/chidian/tests) for some use-cases.

## Feature highlights

| Feature          | In one line                                                                  |
| ---------------- | ---------------------------------------------------------------------------- |
| **Mapper**       | Focused dict→dict runtime transformations with schemas preferred.            |
| **DataMapping**  | Adds Pydantic validation around a `Mapper` for safe, forward-only transforms. |
| **Partials API** | Operator chains with partials module improve conciseness.           |
| **Table**        | Lightweight sparse table: path queries, joins, pandas/polars interop.        |
| **Lexicon**      | Bidirectional code look‑ups *(LOINC ↔ SNOMED)* with defaults + metadata.     |


## Table: DataFrames interoperability

The `Table` class provides seamless conversion to pandas and polars DataFrames via optional dependencies:

### Installation

```bash
# For pandas support
pip install 'chidian[pandas]'

# For polars support
pip install 'chidian[polars]'

# For both
pip install 'chidian[df]'
```

### Usage

```python
from chidian.table import Table

# Create a table
table = Table([
    {"name": "Alice", "age": 30},
    {"name": "Bob", "age": 25}
])

# Convert to pandas (with row keys as index)
df_pd = table.to_pandas(index=True)        # pandas index from row keys

# Convert to polars (with row keys as column)
df_pl = table.to_polars(add_index=True)    # polars gets '_index' column
```

## Flattening nested data

The `Table` class provides powerful flattening capabilities to convert nested dictionaries and lists into flat, column-based structures using intuitive path notation:

```python
from chidian.table import Table

# Create table with nested data
table = Table([
    {"user": {"name": "John", "prefs": ["email", "sms"]}, "id": 123},
    {"user": {"name": "Jane", "prefs": ["phone"]}, "id": 456}
])

# Flatten nested structures
flat = table.flatten()
print(flat.columns)
# {'id', 'user.name', 'user.prefs[0]', 'user.prefs[1]'}

# Direct export with flattening
df = table.to_pandas(flatten=True)     # Flat pandas DataFrame
df = table.to_polars(flatten=True)     # Flat polars DataFrame
table.to_csv("flat.csv", flatten=True) # Flat CSV with path columns

# Control flattening depth and array limits
limited = table.flatten(max_depth=2, array_index_limit=5)
```

**Key features:**
- **Intuitive paths**: `user.name`, `items[0]`, `data.settings.theme`
- **Sparse-friendly**: Different nesting across rows creates union of all paths
- **Special key handling**: Keys with dots/brackets use bracket notation: `["key.with.dots"]`
- **Depth control**: Limit recursion to prevent over-flattening
- **Array limits**: Cap array indices to manage large arrays
- **Seamless integration**: All Table operations (join, select, group_by) work on flattened data

## Powered by Pydantic

chidian treats **Pydantic v2 models as first‑class citizens**:

* Validate inputs & outputs automatically with Pydantic v2
* `DataMapping` wraps your `Mapper` for IDE completion & mypy.
* You can drop down to plain dicts when prototyping with `strict=False`.


## Motivation + Philosophy

This is a library for data engineers by a data engineer. Data engineering touches many parts of the stack, and the heuristics for data engineering offer some subtle differences from traditional software engineering.

The goals of the library are:
1. Make fast, reliable, and readable data mappings
2. Make it easy to build-on + share pre-existing mappings (so we don't need to start from scratch every time!)

Several challenges come up with traditional data mapping code:
1. **It's verbose**: Data can be very messy and has a lot of edge cases
2. **It's hard to share**: Code is often written for one-off use-cases
3. **It's difficult to collaborate**: Data interoperability becomes more difficult when subtle cases

chidian aims to solve these issues by taking stronger opinions on common operations:
1. **Prefer iteration over exactness**: With data, we learn as we iterate and use what we need!
2. **Prefer using functions as objects**: Simplify code by passing functions as first-class objects.
3. **Prefer JSON-like structures**: No toml, yaml, xml -- just JSON (for now...).

The heart of chidian is applying [functional programming](https://en.wikipedia.org/wiki/Functional_programming) principles to data mappings.
Ideas from this repo are inspired from functional programming and other libraries (e.g. [Pydantic](https://github.com/pydantic/pydantic), [JMESPath](https://github.com/jmespath), [funcy](https://github.com/Suor/funcy), [Boomerang](https://github.com/boomerang-lang/boomerang/tree/master), [lens](https://hackage.haskell.org/package/lens), etc.)

## Contributing

All contributions welcome! Please open an Issue and tag me -- I'll make sure to get back to you and we can scope out a PR.
