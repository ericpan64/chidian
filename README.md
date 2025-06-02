# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Declarative, type‑safe data mapping for humans. Backed by Rust speed and the Pydantic ecosystem.

chidian is a cross-language framework for composable, readable, and sharable data mappings built on top of Pydantic.

## Install
```
pip install chidian   # Python ≥ 3.8
```
The wheel bundles the Rust core; no system toolchain required.

## 30-second tour
```python
from pydantic import BaseModel
from chidian import DataMapping, Piper, template
import chidian.partials as p

# 🎙️ 1. Describe your schemas
class Source(BaseModel):
    name: dict
    address: dict

class Target(BaseModel):
    full_name: str
    address: str

# 🔎 2. Define mapping logic with helpful partial functions
fmt = p.template("{} {} {}", skip_none=True)
person_mapping = DataMapping(
    Source,
    Target,
    mapping=lambda src: {
        "full_name": fmt(
            p.get("name.first")(src),
            p.get("name.given[*]") >> p.join(" ")(src),
            p.get("name.suffix")(src),
        ),
        "address": p.get("address") >> p.flatten_paths(
            ["street[0]", "street[1]", "city", "postal_code", "country"],
            delimiter="\n"
        )(src),
    }
)

# 🌱 3. Create runtime and execute transformation
piper = Piper(person_mapping)
target_record = piper(source_data)

# For bidirectional mappings, use simple path mappings:
bidirectional_mapping = DataMapping(
    Source,
    Target,
    mapping={
        "name.first": "full_name",
        "address": "address"
    },
    bidirectional=True,
)

# ⏪ Reverse transform (B → A) – zero extra code!
bidirectional_piper = Piper(bidirectional_mapping)
target, spillover = bidirectional_piper(source_data)
source_roundtrip = bidirectional_piper.reverse(target, spillover)
```

See the [tests](/chidian-py/tests) for some use-cases.

## Feature highlights

| Feature          | In one line                                                                  |
| ---------------- | ---------------------------------------------------------------------------- |
| **Piper**        | Runtime engine for executing DataMapping transformations between Pydantic models. |
| **DataMapping**  | Unidirectional or bidirectional mappings between Pydantic models with callable logic support. |
| **Partials API** | `>>` operator chains (`split >> last >> upper`) keep lambdas away.           |
| **RecordSet**    | Lightweight collection class: `select`, `filter`, `to_json`, arrow export.   |
| **Lexicon**      | Bidirectional code look‑ups *(LOINC ↔ SNOMED)* with defaults + metadata.     |


## Powered by Pydantic

chidian treats **Pydantic v2 models as first‑class citizens**:

* Validate inputs & outputs automatically with Pydantic v2
* `Piper` attaches models to your pipeline for IDE completion & mypy.
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
