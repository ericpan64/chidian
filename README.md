# chidian - <ins alt="chi">chi</ins>meric <ins alt="d̲">d</ins>ata <ins alt="i̲">i</ins>nterch<ins alt="a̲n̲">an</ins>ge

chidian is a cross-language framework for composable, readable, and sharable data mappings. We define a "data mapping" as a series of operations that convert one data schema into a well-structured targeted schema. chidian is written in Rust and exports bindings to Python (via PyO3 + maturin -- in-progress) and JavaScript (via wasm-bindgen -- in-progress).

## Overview

The heart of chidian is applying [functional programming](https://en.wikipedia.org/wiki/Functional_programming) principles to data mappings. The goals of the library are:
1. Make fast, reliable, and readable data mappings
2. Make it easy to build-on + share pre-existing mappings (so we don't need to start from scratch every time!)

There is one core datatype in chidian: the dictionary with string-based keys (`dict[str, Any]` in Python, `Object` in JavaScript, `HashMap<str, ...>` in Rust).

## Motivation

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

## Usage

Let's say we want to conver this source JSON A:
```json
{
    "name": {
        "first": "Bob",
        "given": [
            "S",
            "Figgens"
        ],
        "prefix": null,
        "suffix": "Sr."
    },
    "address": {
        "current": {
            "street": [
                "123 Privet Drive",
                "Little Whinging"
            ],
            "city": "Surrey",
            "state": "England",
            "postal_code": "AB12 3CD",
            "country": "United Kingdom"
        },
        "previous": [
            {
                "street": [
                    "221B Baker Street",
                    "Marylebone"
                ],
                "city": "London",
                "state": "England",
                "postal_code": "NW1 6XE",
                "country": "United Kingdom"
            },
            {
                "street": [
                    "12 Grimmauld Place",
                    "Islington"
                ],
                "city": "London",
                "state": "England",
                "postal_code": "N1 3AX",
                "country": "United Kingdom"
            }
        ]
    }
}
```
into this result JSON B (note: we take the end of the `previous` list):
```json
{
    "full_name": "Bob S Figgens Sr.",
    "current_address": "123 Privet Drive\nLittle Whinging\nSurrey\nAB12 3CD\nUnited Kingdom",
    "last_previous_address": "12 Grimmauld Place\nIslington\nLondon\nN1 3AX\nUnited Kingdom"
}
```

### A -> B

In Python:
```python
from chidian import get, Mapper
import chidian.partials as p

def A_to_B_fn(source: dict) -> dict:
    # Define components as objects (allows reuse)
    address_key = "address.current.(street[*], city, state, postal_code, country)"
    address_ops = [p.flatten_lists, p.remove_empty, p.join("\n")]

    # Quickly see data mapping in way that matches the data schema
    return {
        "full_name": get(source, "name.(prefix, first, given[*], suffix)", 
                        apply=[p.flatten_lists, p.remove_empty, p.join(" ")]),
        "current_address": get(source, address_key, apply=address_ops),
        "last_previous_address": get(source, address_key, apply=address_ops)
    }

A_to_B_mapper = Mapper(mapping_fn=A_to_B_fn)
```

In JavaScript:
```javascript
import { get, Mapper } from 'chidian';
import * as p from 'chidian/partials';

const A_to_B_fn = (source) => {
    // Define components as objects (allows reuse)
    const addressKey = "address.current.(street[*], city, state, postal_code, country)";
    const addressOps = [p.flatten_lists, p.remove_empty, p.join("\n")];

    // Quickly see data mapping in way that matches the data schema
    return {
        full_name: get(source, "name.(prefix, first, given[*], suffix)", 
                    { apply: [p.flatten_lists, p.remove_empty, p.join(" ")] }),
        current_address: get(source, addressKey, { apply: addressOps }),
        last_previous_address: get(source, addressKey, { apply: addressOps })
    };
};

const A_to_B_mapper = new Mapper({ mapping_fn: A_to_B_fn });
```

### B -> A

In Python:
```python
from chidian import get, Mapper
import chidian.partials as p

def B_to_A_fn(source: dict) -> dict:
    # Parse name
    parsed_name = get(source, "full_name", apply=[p.split(" ")])
    # Check if prefix and suffix (assume can tell with ".")
    has_prefix = "." in parsed_name[0] if parsed_name else False
    has_suffix = "." in parsed_name[-1] if parsed_name else False
    has_both = has_prefix and has_suffix
    # Parse address
    parsed_current_address = get(source, "current_address", apply=[p.split("\n")])
    parsed_last_previous_address = get(source, "last_previous_address", apply=[p.split("\n")])
    return {
        "name": {
            "first": parsed_name[1] if has_prefix else parsed_name[0],
            "given": parsed_name[p.case({
                has_both: slice(2,-2),
                has_suffix: slice(1,-2),
                has_prefix: slice(2,-1),
                True: slice(1,-1)
            })],
            "prefix": parsed_name[0] if has_prefix else None,
            "suffix": parsed_name[-1] if has_suffix else None
        },
        "address": {
            "current": {
                "street": [
                    parsed_current_address[0],
                    parsed_current_address[1] 
                ],
                "city": parsed_current_address[2],
                "state": parsed_current_address[3],
                "postal_code": parsed_current_address[4],
                "country": parsed_current_address[5]
            },
            "previous": [{
                "street": [
                    parsed_last_previous_address[0],
                    parsed_last_previous_address[1] 
                ],
                "city": parsed_last_previous_address[2],
                "state": parsed_last_previous_address[3],
                "postal_code": parsed_last_previous_address[4],
                "country": parsed_last_previous_address[5]
            }]
        }
    }

B_to_A_mapper = Mapper(mapping_fn=B_to_A_fn)
```

In JavaScript:
```javascript
import { get, Mapper } from 'chidian';
import * as p from 'chidian/partials';

const B_to_A_fn = (source) => {
    // Parse name
    const parsed_name = get(source, "full_name", { apply: [p.split(" ")] });
    // Check if prefix and suffix (assume can tell with ".")
    const has_prefix = parsed_name ? parsed_name[0].includes(".") : false;
    const has_suffix = parsed_name ? parsed_name[parsed_name.length - 1].includes(".") : false;
    const has_both = has_prefix && has_suffix;
    
    // Parse address
    const parsed_current_address = get(source, "current_address", { apply: [p.split("\n")] });
    const parsed_last_previous_address = get(source, "last_previous_address", { apply: [p.split("\n")] });
    
    return {
        "name": {
        "first": has_prefix ? parsed_name[1] : parsed_name[0],
        "given": parsed_name[p.case({
            [has_both]: { start: 2, end: -2 },
            [has_suffix]: { start: 1, end: -2 },
            [has_prefix]: { start: 2, end: -1 },
            [true]: { start: 1, end: -1 }
        })],
        "prefix": has_prefix ? parsed_name[0] : null,
        "suffix": has_suffix ? parsed_name[parsed_name.length - 1] : null
        },
        "address": {
        "current": {
            "street": [
            parsed_current_address[0],
            parsed_current_address[1]
            ],
            "city": parsed_current_address[2],
            "state": parsed_current_address[3],
            "postal_code": parsed_current_address[4],
            "country": parsed_current_address[5]
        },
        "previous": [{
            "street": [
            parsed_last_previous_address[0],
            parsed_last_previous_address[1]
            ],
            "city": parsed_last_previous_address[2],
            "state": parsed_last_previous_address[3],
            "postal_code": parsed_last_previous_address[4],
            "country": parsed_last_previous_address[5]
        }]
        }
    };
};

const B_to_A_mapper = new Mapper({ mapping_fn: B_to_A_fn });
```
