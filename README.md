# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

> Work-in-progress -- v0.1 will be out soon!

chidian is a cross-language framework for composable, readable, and sharable data mappings built on top of Pydantic. chidian focuses on the key-value dictionary as the core data type (`dict[str, Any]` in Python) and aims to make writing data mappings both less tedious and more fun!

chidian is _not_ currently a data processing framework -- it is focused specifically on data transformations between well-defined Pydantic classes and helper functions to make this easier. Ideas from this repo are inspired from functional programming and other libraries (e.g. [Pydantic](https://github.com/pydantic/pydantic), [JMESPath](https://github.com/jmespath), [funcy](https://github.com/Suor/funcy), [Boomerang](https://github.com/boomerang-lang/boomerang/tree/master), [lens](https://hackage.haskell.org/package/lens), etc.)

We define a "data mapping" as a series of operations that convert one data schema into a well-structured targeted schema. chidian is written in Rust and exports bindings to Python (via PyO3 + maturin -- in-progress) and JavaScript (via wasm-bindgen -- in-progress).

## Overview

The heart of chidian is applying [functional programming](https://en.wikipedia.org/wiki/Functional_programming) principles to data mappings.

The goals of the library are:
1. Make fast, reliable, and readable data mappings
2. Make it easy to build-on + share pre-existing mappings (so we don't need to start from scratch every time!)

There is one core datatype in chidian: the dictionary with string-based keys (`dict[str, Any]` in Python, `Object` in JavaScript, `HashMap<str, ...>` in Rust).

The file structure is organized into the core abstractions of the library (re-ordered most essential first):
```
.
├── LICENSE
├── README.md
└── chidian-py
    ├── Cargo.lock
    ├── Cargo.toml
    ├── chidian
    │   ├── __init__.py
    │   ├── lib.py      # `get` + `put` -- the core functions (bi-directional inverses)
    │   ├── group.py    # `DataCollection` -- the core data wrapper (use in conjunction with Pydantic `BaseModel`s)
    │   ├── mapper.py   # `StringMapper` + `StructMapper` -- the core mapping logic expressed as readable `dict[str, Any]`
    │   ├── piper.py    # `DictPiper` -- the core mapping runtime/execution class
    │   ├── seeds.py    # `DROP`, `KEEP`, etc. -- utilities to help keep readings mappable (Piper processes them)
    │   └── partials.py # `import partials as p` -- a set of standard operations expressed as partial functions (Rust-optimized)
    ├── pyproject.toml
    ├── src/...         # Rust optimizations for libraries
    ├── tests/...       # Tests for each python module
    └── uv.lock
```

## Usage

Let's say we want to conver this source [JSON A](./chidian-py/tests/A.json) into this result [JSON B](./chidian-py/tests/B.json) (note: we take the end of the `previous` list).

If you look at the data, JSON A is _more nested + expressive_ and JSON B is _more flat + compressed_. 

We can balance the expressiveness of then nesting through the expressive structure of the `StructMapper`

### A -> B

In Python:
```python
from chidian import get, DictPiper, StringMapper
from chidian.seeds import MERGE, FLAT, MAIN, COAL
import chidian.partials as p

from pydantic import BaseModel

# Define A and B structs in pydantic
# `A.json`
class A(BaseModel):
    ...

# `B.json`
class B(BaseModel):
    ...

def A_to_B_fn(source: A) -> B:
    # Define reusable address formatter using MERGE
    address_formatter = MERGE(
        template="{street}\n{city}\n{state}\n{postal_code}\n{country}",
        sources={
            'street': FLAT('street[*]', p.join("\n")),
            'city': 'city',
            'state': 'state', 
            'postal_code': 'postal_code',
            'country': 'country'
        }
    )

    # Quickly see data mapping in way that matches the data schema
    return {
        "full_name": MERGE(
            template="{prefix} {first} {given} {suffix}",
            sources={
                'prefix': COAL('name.prefix', KEEP('')),
                'first': 'name.first',
                'given': FLAT('name.given[*]', p.join(" ")),
                'suffix': COAL('name.suffix', KEEP(''))
            },
            apply=[p.remove_empty, p.join(" ")]
        ),
        "current_address": get(source, "address.current", apply=[address_formatter]),
        "last_previous_address": get(source, "address.previous[-1]", apply=[address_formatter])
    }

A_to_B_mapper = DictPiper(mapping_fn=A_to_B_fn)
```

### B -> A

In Python:
```python
from chidian import get, Mapper
from chidian.seeds import SPLIT, ELIF
import chidian.partials as p

def B_to_A_fn(source: dict) -> dict:
    # Define name parsing with pattern matching
    name_splitter = SPLIT(
        pattern=" ",  # Split on spaces
        targets={
            'prefix': {'index': 0, 'condition': lambda s: "." in s},
            'first': {'index': 0, 'skip_if': 'prefix'},
            'given': {'slice': (1, -1), 'adjust_for': ['prefix', 'suffix']},
            'suffix': {'index': -1, 'condition': lambda s: "." in s}
        }
    )
    
    # Define address parsing with positional mapping
    address_splitter = SPLIT(
        pattern="\n",  # Split on newlines
        targets={
            'street': {'slice': (0, 2)},
            'city': {'index': 2},
            'state': {'index': 3},
            'postal_code': {'index': 4},
            'country': {'index': 5}
        }
    )
    
    return {
        "name": get(source, "full_name", apply=[name_splitter]),
        "address": {
            "current": get(source, "current_address", apply=[address_splitter]),
            "previous": [
                get(source, "last_previous_address", apply=[address_splitter])
            ]
        }
    }

B_to_A_mapper = Mapper(mapping_fn=B_to_A_fn)
```

## Motivation + Philosophy

This is a library for data engineers by a data engineer. Data engineering touches many parts of the stack, and while the core of the work does involve software, the heuristics for data engineering offer some subtle differences from traditional software engineering.

A common data mapping has the following components (converting from a `source` object to a `result` object):
```
start with `source`
FOR EACH field in `source` (1..n):
    If field is required for `result`:
        Grab data from the `source.field_i`
        Apply 0..m transformations on `source.field_i`
        Place `source.field_i_transformed` into the right place in `result`
return `result`
```

Simple, right? Generally it is! However several challenges come up with traditional data mapping code:
1. **It's difficult to write concisely**: Data can be very messy and has a lot of edge cases
2. **It's hard to share**: Code is often written for one-off use-cases
3. **It's difficult to collaborate**: Data interoperability becomes more difficult when subtle cases 

chidian aims to solve these issues by taking stronger opinions on common operations:
1. **Prefer iteration over exactness**: Instead of crashing at the first error... just keep going. With data, we learn as we iterate and use what we need!
2. **Prefer using functions as objects**: Simplify code by passing functions as first-class objects -- a feature of many modern programming languages.
3. **Prefer JSON-like structures**: No toml, yaml, xml -- just JSON (for now...).

## Contributing

All contributions welcome! Please open a PR and tag me -- I'll make sure to get back to you!
