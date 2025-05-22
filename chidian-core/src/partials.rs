// TODO: Port from python impl (use fp_core crate?)

// Partial application utility functions for functional programming
// Ported from Python implementation

use std::cmp::Ordering;
use std::error::Error;
use std::fmt;
use std::ops::{Add, Div, Mul, Sub};
use serde_json::Value;
use std::collections::HashMap;

use crate::Chainable;
use crate::mapper::MappingContext;

/// Generic type for function wrappers - a function that takes a value and returns a result
pub type ApplyFn<T, U> = Box<dyn Fn(T) -> U>;

/// Wrapper struct that adapts ApplyFn to implement Chainable
pub struct Partial<F> {
    func: F,
    name: String,
}

impl<F> Partial<F> 
where 
    F: Fn(Value) -> Result<Value, Box<dyn Error>> + 'static
{
    /// Creates a new Partial from an ApplyFn
    pub fn new(func: F, name: String) -> Self {
        Partial { func, name }
    }
}

impl<F> Chainable for Partial<F> 
where 
    F: Fn(Value) -> Result<Value, Box<dyn Error>> + 'static
{
    fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
        let result = (self.func)(context.data)?;
        Ok(MappingContext {
            data: result,
            metadata: context.metadata,
        })
    }

    fn name(&self) -> String {
        self.name.clone()
    }
}

/// Simple chainable that just carries options
pub struct OptionsChainable {
    flatten: bool,
    strict: bool,
    default_value: Option<Value>,
}

impl Chainable for OptionsChainable {
    fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
        let mut data = context.data;
        
        // Apply default value if data is null
        if let Some(ref default) = self.default_value {
            if data.is_null() {
                data = default.clone();
            }
        }
        
        // Apply flatten if enabled
        if self.flatten {
            data = flatten_value(data);
        }
        
        Ok(MappingContext {
            data,
            metadata: context.metadata,
        })
    }

    fn name(&self) -> String {
        format!("Options(flatten={}, strict={}, has_default={})", 
                self.flatten, self.strict, self.default_value.is_some())
    }
}

fn flatten_value(value: Value) -> Value {
    match value {
        Value::Array(arr) => {
            let mut result = Vec::new();
            for item in arr {
                match item {
                    Value::Array(inner_arr) => {
                        for inner_item in inner_arr {
                            if !inner_item.is_null() {
                                result.push(inner_item);
                            }
                        }
                    },
                    other if !other.is_null() => result.push(other),
                    _ => {}
                }
            }
            Value::Array(result)
        },
        other => other,
    }
}

// Helper function to create a Partial
pub fn to_chainable<F>(func: F, name: &str) -> Box<dyn Chainable>
where
    F: Fn(Value) -> Result<Value, Box<dyn Error>> + 'static,
{
    Box::new(Partial::new(func, name.to_string()))
}

// Adapter function for simple functions without error handling
pub fn adapt_simple<F, T, U>(func: F) -> impl Fn(Value) -> Result<Value, Box<dyn Error>>
where
    F: Fn(T) -> U + 'static,
    T: serde::de::DeserializeOwned,
    U: serde::Serialize,
{
    move |value| {
        let input = serde_json::from_value(value.clone())
            .map_err(|e| Box::new(e) as Box<dyn Error>)?;
        let output = func(input);
        Ok(serde_json::to_value(output)
            .map_err(|e| Box::new(e) as Box<dyn Error>)?)
    }
}

/// Options with flatten
pub fn options_with_flatten(flatten: bool) -> Box<dyn Chainable> {
    Box::new(OptionsChainable {
        flatten,
        strict: false,
        default_value: None,
    })
}

/// Options with strict mode
pub fn options_with_strict(strict: bool) -> Box<dyn Chainable> {
    Box::new(OptionsChainable {
        flatten: false,
        strict,
        default_value: None,
    })
}

/// Convert string to uppercase
pub fn to_uppercase() -> Box<dyn Chainable> {
    to_chainable(|value| {
        match value {
            Value::String(s) => Ok(Value::String(s.to_uppercase())),
            other => Ok(other),
        }
    }, "to_uppercase")
}

/// Append a string to the input string
pub fn append_string(suffix: &str) -> Box<dyn Chainable> {
    let suffix = suffix.to_string();
    let name = format!("append_string({})", suffix);
    to_chainable(move |value| {
        match value {
            Value::String(s) => Ok(Value::String(format!("{}{}", s, suffix))),
            other => Ok(other),
        }
    }, &name)
}

/// Replace a substring in a string
pub fn replace_string(old: &str, new: &str) -> Box<dyn Chainable> {
    let old = old.to_string();
    let new = new.to_string();
    let name = format!("replace_string({}, {})", old, new);
    to_chainable(move |value| {
        match value {
            Value::String(s) => Ok(Value::String(s.replace(&old, &new))),
            other => Ok(other),
        }
    }, &name)
}

/// Chain multiple chainable operations
pub fn chain(chainables: Vec<Box<dyn Chainable>>) -> Box<dyn Chainable> {
    Box::new(ChainChainable { chainables })
}

struct ChainChainable {
    chainables: Vec<Box<dyn Chainable>>,
}

impl Chainable for ChainChainable {
    fn run(&self, mut context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
        for chainable in &self.chainables {
            context = chainable.run(context)?;
        }
        Ok(context)
    }

    fn name(&self) -> String {
        let names: Vec<String> = self.chainables.iter().map(|c| c.name()).collect();
        format!("chain({})", names.join(" -> "))
    }
}

/// Always return None/null (fails the chain)
pub fn always_none() -> Box<dyn Chainable> {
    to_chainable(|_| {
        Err("always_none always fails".into())
    }, "always_none")
}

/// Check if string starts with prefix
pub fn starts_with(prefix: &str) -> Box<dyn Chainable> {
    let prefix = prefix.to_string();
    let name = format!("starts_with({})", prefix);
    to_chainable(move |value| {
        match value {
            Value::String(s) => {
                if s.starts_with(&prefix) {
                    Ok(Value::Bool(true))
                } else {
                    Err("String does not start with prefix".into())
                }
            },
            _ => Err("Value is not a string".into()),
        }
    }, &name)
}

/// Filter based on a condition - only pass through if condition passes
pub fn with_filter(condition: Box<dyn Chainable>, then_apply: Box<dyn Chainable>) -> Box<dyn Chainable> {
    Box::new(FilterChainable {
        condition,
        then_apply,
    })
}

struct FilterChainable {
    condition: Box<dyn Chainable>,
    then_apply: Box<dyn Chainable>,
}

impl Chainable for FilterChainable {
    fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
        // First check the condition
        let condition_result = self.condition.run(context.clone_data());
        match condition_result {
            Ok(_) => {
                // Condition passed, apply the transform
                self.then_apply.run(context)
            },
            Err(_) => {
                // Condition failed
                Err("Filter condition failed".into())
            }
        }
    }

    fn name(&self) -> String {
        format!("with_filter({} -> {})", self.condition.name(), self.then_apply.name())
    }
}

/// Provide a default value if input is null
pub fn with_default<T: Into<Value>>(default_value: T) -> Box<dyn Chainable> {
    let default = default_value.into();
    let name = format!("with_default({:?})", default);
    to_chainable(move |value| {
        fn replace_nulls(value: Value, default: &Value) -> Value {
            match value {
                Value::Null => default.clone(),
                Value::Array(arr) => {
                    let replaced: Vec<Value> = arr.into_iter()
                        .map(|item| replace_nulls(item, default))
                        .collect();
                    Value::Array(replaced)
                },
                Value::Object(obj) => {
                    let replaced: serde_json::Map<String, Value> = obj.into_iter()
                        .map(|(k, v)| (k, replace_nulls(v, default)))
                        .collect();
                    Value::Object(replaced)
                },
                other => other,
            }
        }
        
        Ok(replace_nulls(value, &default))
    }, &name)
}

/// Get array element by index (supports negative indexing)
pub fn index(idx: i32) -> Box<dyn Chainable> {
    to_chainable(move |value| {
        match value {
            Value::Array(arr) => {
                let len = arr.len() as i32;
                let actual_idx = if idx < 0 {
                    len + idx
                } else {
                    idx
                };
                
                if actual_idx >= 0 && (actual_idx as usize) < arr.len() {
                    Ok(arr[actual_idx as usize].clone())
                } else {
                    Err(format!("Index {} out of bounds for array of length {}", idx, len).into())
                }
            },
            other => Err(format!("Cannot index into non-array value: {:?}", other).into()),
        }
    }, &format!("index({})", idx))
}

/// Always return false (for testing filter failures)
pub fn always_false() -> Box<dyn Chainable> {
    to_chainable(|_| {
        Err("always_false always fails".into())
    }, "always_false")
}

/// Identity function - returns input unchanged
pub fn identity() -> Box<dyn Chainable> {
    to_chainable(|value| Ok(value), "identity")
}

/// Create a chainable that wraps the keep function to work with the Chainable trait
pub fn keep(n: usize) -> Box<dyn Chainable> {
    to_chainable(move |value| {
        match value {
            Value::Array(arr) => {
                let result: Vec<Value> = arr.into_iter().take(n).collect();
                Ok(Value::Array(result))
            },
            other => Ok(other), // Non-arrays pass through unchanged
        }
    }, &format!("keep({})", n))
}

/// Wraps a function and argument(s) to create a new function that applies the original
/// function to its input plus the provided arguments.
///
/// Equivalent to Python's `functools.partial` but applies the input as the first argument.
pub fn do_fn<T, U, V, F>(func: F, arg: V) -> ApplyFn<T, U>
where
    F: Fn(T, V) -> U + 'static,
    V: Clone + 'static,
{
    Box::new(move |x| func(x, arg.clone()))
}

/// Returns a function that always returns the provided value, ignoring its input.
pub fn echo<T, V>(v: V) -> ApplyFn<T, V>
where
    V: Clone + 'static,
{
    Box::new(move |_| v.clone())
}

/// Returns a function that adds a value to its input.
pub fn add<T>(value: T, before: bool) -> ApplyFn<T, T>
where
    T: Add<Output = T> + Clone + 'static,
{
    if before {
        Box::new(move |v| value.clone() + v)
    } else {
        Box::new(move |v| v + value.clone())
    }
}

/// Returns a function that subtracts a value from its input (or vice versa if before=true).
pub fn subtract<T>(value: T, before: bool) -> ApplyFn<T, T>
where
    T: Sub<Output = T> + Clone + 'static,
{
    if before {
        Box::new(move |v| value.clone() - v)
    } else {
        Box::new(move |v| v - value.clone())
    }
}

/// Returns a function that multiplies its input by a value.
pub fn multiply<T>(value: T, before: bool) -> ApplyFn<T, T>
where
    T: Mul<Output = T> + Clone + 'static,
{
    if before {
        Box::new(move |v| value.clone() * v)
    } else {
        Box::new(move |v| v * value.clone())
    }
}

/// Returns a function that divides its input by a value (or vice versa if before=true).
pub fn divide<T>(value: T, before: bool) -> ApplyFn<T, T>
where
    T: Div<Output = T> + Clone + 'static,
{
    if before {
        Box::new(move |v| value.clone() / v)
    } else {
        Box::new(move |v| v / value.clone())
    }
}

/// Returns a function that checks if its input equals a value.
pub fn equals<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialEq + Clone + 'static,
{
    Box::new(move |v| v == value.clone())
}

/// Returns a function that checks if its input is greater than a value.
pub fn gt<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialOrd + Clone + 'static,
{
    Box::new(move |v| v > value.clone())
}

/// Returns a function that checks if its input is less than a value.
pub fn lt<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialOrd + Clone + 'static,
{
    Box::new(move |v| v < value.clone())
}

/// Returns a function that checks if its input is greater than or equal to a value.
pub fn gte<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialOrd + Clone + 'static,
{
    Box::new(move |v| v >= value.clone())
}

/// Returns a function that checks if its input is less than or equal to a value.
pub fn lte<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialOrd + Clone + 'static,
{
    Box::new(move |v| v <= value.clone())
}

/// Returns a function that checks if its input is not equal to a value.
pub fn not_equal<T>(value: T) -> ApplyFn<T, bool>
where
    T: PartialEq + Clone + 'static,
{
    Box::new(move |v| v != value.clone())
}

/// Returns a function that maps a function over a collection and collects the results.
pub fn map_to_vec<T, U, F>(f: F) -> ApplyFn<Vec<T>, Vec<U>>
where
    F: Fn(T) -> U + Clone + 'static,
    T: 'static,
    U: 'static,
{
    Box::new(move |items| items.into_iter().map(|item| f.clone()(item)).collect())
}

/// Returns a function that filters a collection using a predicate and collects the results.
pub fn filter_to_vec<T, F>(f: F) -> ApplyFn<Vec<T>, Vec<T>>
where
    F: Fn(&T) -> bool + Clone + 'static,
    T: 'static,
{
    Box::new(move |items| {
        items
            .into_iter()
            .filter(|item| f.clone()(item))
            .collect()
    })
}

// More advanced functions like `index` with negative indices, `contains`,
// `contained_in`, etc. could be implemented as needed.
