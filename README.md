# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> Declarative, type-safe data mapping for humans.

chidian is a pure Python framework for composable, readable, and sharable data mappings built on top of **Pydantic v2**.

## 30-second tour
```python
from pydantic import BaseModel
from chidian import Mapper, DataMapping
import chidian.partials as p

# 1️⃣ Define your source & target schemas
class Source(BaseModel):
    name: dict
    address: dict

class Target(BaseModel):
    full_name: str
    address: str

# 2️⃣ Write pure dict→dict transformation logic with `Mapper`
fmt = p.template("{} {} {}", skip_none=True)

person_mapper = Mapper(
    lambda src: {
        "full_name": fmt(
            p.get("name.first")(src),
            p.get("name.given[*]") | p.join(" ")(src),
            p.get("name.suffix")(src),
        ),
        "address": p.get("address") | p.flatten_paths(
            [
                "street[0]",
                "street[1]",
                "city",
                "postal_code",
                "country",
            ],
            delimiter="\n",
        )(src),
    }
)

# 3️⃣ Wrap it with `DataMapping` for schema validation
person_mapping = DataMapping(
    mapper=person_mapper,
    input_schema=Source,
    output_schema=Target,
)

# 4️⃣ Execute!
source_obj = Source.model_validate(source_data)
result = person_mapping.forward(source_obj)
print(result)
```

See the [tests](/chidian/tests) for some use-cases.

## Feature highlights

| Feature          | In one line                                                                  |
| ---------------- | ---------------------------------------------------------------------------- |
| **Mapper**       | Pure dict→dict runtime transformations – no schema required.                 |
| **DataMapping**  | Adds Pydantic validation around a `Mapper` for safe, forward-only transforms. |
| **Partials API** | `|` operator chains (`split | last | upper`) keep lambdas away.           |
| **DictGroup**    | Lightweight collection class: `select`, `filter`, `to_json`, arrow export.   |
| **Lexicon**      | Bidirectional code look‑ups *(LOINC ↔ SNOMED)* with defaults + metadata.     |


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
