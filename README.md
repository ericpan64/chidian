# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

> Work-in-progress -- v0.1 will be out soon!

chidian is a cross-language framework for composable, readable, and sharable data mappings built on top of Pydantic. chidian is written in Rust and exports bindings to Python (via PyO3 + maturin).

chidian focuses on the key-value dictionary as the core data type (`dict[str, Any]`) and aims to make writing data mappings both less tedious and more fun!

We define a "data mapping" as a series of operations that convert one data schema into a well-structured targeted schema. 


See the [example usage](#usage) below.

## Motivation + Philosophy

This is a library for data engineers by a data engineer. Data engineering touches many parts of the stack, and while the core of the work does involve software, the heuristics for data engineering offer some subtle differences from traditional software engineering.

Several challenges come up with traditional data mapping code:
1. **It's difficult to write concisely**: Data can be very messy and has a lot of edge cases
2. **It's hard to share**: Code is often written for one-off use-cases
3. **It's difficult to collaborate**: Data interoperability becomes more difficult when subtle cases 

chidian aims to solve these issues by taking stronger opinions on common operations:
1. **Prefer iteration over exactness**: Instead of crashing at the first error... just keep going. With data, we learn as we iterate and use what we need!
2. **Prefer using functions as objects**: Simplify code by passing functions as first-class objects -- a feature of many modern programming languages.
3. **Prefer JSON-like structures**: No toml, yaml, xml -- just JSON (for now...).

The heart of chidian is applying [functional programming](https://en.wikipedia.org/wiki/Functional_programming) principles to data mappings.
Ideas from this repo are inspired from functional programming and other libraries (e.g. [Pydantic](https://github.com/pydantic/pydantic), [JMESPath](https://github.com/jmespath), [funcy](https://github.com/Suor/funcy), [Boomerang](https://github.com/boomerang-lang/boomerang/tree/master), [lens](https://hackage.haskell.org/package/lens), etc.)

## Overview

The goals of the library are:
1. Make fast, reliable, and readable data mappings
2. Make it easy to build-on + share pre-existing mappings (so we don't need to start from scratch every time!)

The file structure is organized into the core abstractions of the library (re-ordered most essential first):
```
./chidian
├── LICENSE
├── README.md
├── chidian-core/           # Core Rust library for path parsing and data types
│   ├── Cargo.toml
│   └── src/
│       ├── lib.rs          # Re-exports for core functionality 
│       ├── parser.rs       # Path parsing logic (JMESPath-inspired)
│       └── types.rs        # Core data types and structures
└── chidian-py/             # Python bindings and main API
    ├── Cargo.toml
    ├── chidian/
    │   ├── __init__.py     # Main exports
    │   ├── lib.py          # `put` -- bidirectional complement to `get`
    │   ├── lens.py         # `Lens` -- functional composition for data transformations
    │   ├── recordset.py    # `RecordSet` -- the core data wrapper for dict collections
    │   ├── lexicon.py      # `Lexicon` -- bidirectional string-to-string mappings (e.g., code lookups)
    │   ├── view.py         # `View` -- structured data transformations with Pydantic models
    │   ├── piper.py        # `DictPiper`, `TypedPiper` -- the core mapping runtime/execution classes
    │   ├── seeds.py        # `DROP`, `KEEP`, `CASE`, `MERGE`, etc. -- SEED objects for data transformations
    │   └── partials.py     # `import partials as p` -- standard operations as partial functions
    ├── pyproject.toml
    ├── src/                # Rust code for Python bindings
    │   ├── lib.rs          # PyO3 bindings
    │   └── py_traversal.rs # Rust-optimized `get` function
    ├── tests/              # Tests for each Python module
    └── uv.lock
```

## Usage

Let's say we want to convert this source [JSON A](./chidian-py/tests/A.json) into this result [JSON B](./chidian-py/tests/B.json) (note: we take the last of the `previous` list).

If you look at the data, JSON A is _more nested + expressive_ and JSON B is _more flat + compressed_. 

chidian makes this transformation easy with its functional approach and composable operations.

### A -> B

In Python:
```python
from chidian import get, DictPiper, template
import chidian.partials as p

def A_to_B(source):
    # Define reusable transformations
    format_address = [
        lambda addr: f"{addr['street'][0]}\n{addr['street'][1]}\n{addr['city']}\n{addr['postal_code']}\n{addr['country']}"
    ]
    
    # Use new partials API for cleaner composition
    full_name_formatter = template("{} {} {}", skip_none=True)
    
    # 80%+ of logic in the mapping dictionary
    return {
        "full_name": full_name_formatter(
            get(source, "name.first"), 
            get(source, "name.given[*]", apply=[p.join(" ")]),
            get(source, "name.suffix")
        ),
        "current_address": get(source, "address.current", apply=format_address),
        "last_previous_address": get(source, "address.previous[-1]", apply=format_address)
    }

# Create and use the mapper
mapper = DictPiper(A_to_B)
result = mapper.pipe(source_data)
```

### B -> A (Reverse transformation)

In Python:
```python
from chidian import get, DictPiper
from chidian.seeds import SPLIT
import chidian.partials as p

def B_to_A(source):
    # Define complex transformations using function chains
    parse_name = (
        p.split() >>  # Split on whitespace
        p.ChainableFn(lambda parts: {
            "first": parts[0] if parts else None,
            "given": parts[1:-1] if len(parts) > 2 else [],
            "suffix": parts[-1] if len(parts) > 1 and "." in parts[-1] else None
        })
    )
    
    parse_address = (
        p.split("\n") >>
        p.ChainableFn(lambda lines: {
            "street": lines[:2] if len(lines) >= 2 else [],
            "city": lines[2] if len(lines) > 2 else "",
            "state": "England",  # Default for this example
            "postal_code": lines[3] if len(lines) > 3 else "",
            "country": lines[4] if len(lines) > 4 else ""
        })
    )
    
    # Bidirectional mapping
    return {
        "name": get(source, "full_name", apply=[parse_name]),
        "address": {
            "current": get(source, "current_address", apply=[parse_address]),
            "previous": [
                get(source, "last_previous_address", apply=[parse_address])
            ]
        }
    }

# Create and use the reverse mapper
reverse_mapper = DictPiper(B_to_A)
original_data = reverse_mapper.pipe(transformed_data)
```

### Additional Features

**Partials Operations** for advanced transformations:
```python
from chidian import case, first_non_empty, DROP, KEEP
import chidian.partials as p

# Conditional logic with partials
status_mapper = (
    p.get("patient.status") >> 
    case({
        "active": "ACTIVE",
        lambda x: x in ["inactive", "deceased"]: "INACTIVE"
    }, default="UNKNOWN")
)
status = status_mapper(data)

# Fallback values using first_non_empty
name = first_non_empty("display_name", "full_name", "name.first")(data)
```

**Functional Composition** with partials:
```python
import chidian.partials as p

# Chain operations with >> operator
process_id = (
    p.get("patient.reference") >>
    p.extract_id() >>
    p.upper
)

# Email domain extraction
domain_extractor = (
    p.get("email") >>
    p.split("@") >>
    p.at_index(1)
)

# Use in transformations
result = {
    "patient_id": process_id(source_data),
    "email_domain": domain_extractor(source_data)
}
```

**Type-Safe Mappings** with Pydantic:
```python
from chidian import View, TypedPiper
from pydantic import BaseModel

class Patient(BaseModel):
    id: str
    name: str
    active: bool

# Define transformation with type safety
patient_view = View(Patient, {
    "id": "patient.id",
    "name": "patient.name.display", 
    "active": "patient.active"
})

typed_mapper = TypedPiper(patient_view)
```

## Contributing

All contributions welcome! Please open an Issue and tag me -- I'll make sure to get back to you and we can scope out a PR.
