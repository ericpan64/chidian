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
    │   ├── lib.py          # `put` -- bidirectional complement to `get` (Rust-optimized)
    │   ├── lens.py         # `put` -- bidirectional complement to `get` (Rust-optimized)
    │   ├── recordset.py    # `RecordSet` -- the core data wrapper for dict collections
    │   ├── mapper.py       # `Mapper` -- base protocol for all data transformations
    │   ├── lexicon.py      # `Lexicon` -- bidirectional string-to-string mappings (e.g., code lookups)
    │   ├── view.py         # `View` -- structured data transformations with Pydantic models
    │   ├── piper.py        # `DictPiper` -- the core mapping runtime/execution class
    │   ├── seeds.py        # `DROP`, `KEEP`, `CASE`, etc. -- SEED objects for data transformations
    │   └── partials.py     # `import partials as p` -- standard operations as partial functions
    ├── pyproject.toml
    ├── src/                # Rust code for Python bindings
    │   ├── lib.rs          # PyO3 bindings
    │   └── py_traversal.rs # Rust-optimized `get` function
    ├── tests/              # Tests for each Python module
    └── uv.lock
```

## Usage

Let's say we want to conver this source [JSON A](./chidian-py/tests/A.json) into this result [JSON B](./chidian-py/tests/B.json) (note: we take the end of the `previous` list).

If you look at the data, JSON A is _more nested + expressive_ and JSON B is _more flat + compressed_. 

We can balance the expressiveness of then nesting through the expressive structure of the `View`

### A -> B

In Python:
```python
from chidian import get, DictPiper
from chidian.seeds import MERGE, FLATTEN
import chidian.partials as p

def A_to_B(source):
    # Define reusable transformations
    format_address = [
        lambda addr: f"{addr['street'][0]}\n{addr['street'][1]}\n{addr['city']}, {addr['state']} {addr['postal_code']}\n{addr['country']}"
    ]
    
    # 80%+ of logic in the mapping dictionary
    return {
        "full_name": MERGE(
            get(source, "name.prefix"),
            get(source, "name.first"), 
            get(source, "name.given[*]", apply=[p.join(" ")]),
            get(source, "name.suffix"),
            template="{} {} {} {}",
            skip_none=True
        ),
        "current_address": get(source, "address.current", apply=format_address),
        "last_previous_address": get(source, "address.previous[-1]", apply=format_address)
    }

mapper = DictPiper(A_to_B)
```

### B -> A

In Python:
```python
from chidian import get, DictPiper
from chidian.seeds import SPLIT, CASE
import chidian.partials as p

def B_to_A(source):
    # Define complex transformations
    parse_name = [
        str.split,
        lambda parts: {
            "prefix": next((p for p in parts if "." in p), None),
            "first": parts[0] if parts and "." not in parts[0] else (parts[1] if len(parts) > 1 else None),
            "given": [p for p in parts[1:-1] if "." not in p] if len(parts) > 2 else [],
            "suffix": parts[-1] if len(parts) > 1 and "." in parts[-1] else None
        }
    ]
    
    parse_address = [
        lambda addr: addr.split("\n"),
        lambda lines: {
            "street": lines[:2] if len(lines) >= 2 else [],
            "city": lines[2].split(",")[0] if len(lines) > 2 else "",
            "state": lines[2].split(",")[1].strip().split()[0] if len(lines) > 2 and "," in lines[2] else "",
            "postal_code": lines[2].split(",")[1].strip().split()[1] if len(lines) > 2 and "," in lines[2] and len(lines[2].split(",")[1].strip().split()) > 1 else "",
            "country": lines[3] if len(lines) > 3 else ""
        }
    ]
    
    # Mapping dictionary with most logic
    return {
        "name": get(source, "full_name", apply=parse_name),
        "address": {
            "current": get(source, "current_address", apply=parse_address),
            "previous": [
                get(source, "last_previous_address", apply=parse_address)
            ]
        }
    }

mapper = DictPiper(B_to_A)
```

## Contributing

All contributions welcome! Please open an Issue and tag me -- I'll make sure to get back to you and we can scope out a PR.
