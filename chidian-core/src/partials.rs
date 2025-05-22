// TODO: Port from python impl (use fp_core crate?)

// Partial application utility functions for functional programming
// Ported from Python implementation

use std::cmp::Ordering;
use std::error::Error;
use std::fmt;
use std::ops::{Add, Div, Mul, Sub};
use serde_json::Value;

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

/// Returns a function that keeps the first n elements of a collection.
pub fn keep<T, C>(n: usize) -> ApplyFn<C, Vec<T>>
where
    C: IntoIterator<Item = T> + 'static,
    T: 'static,
{
    Box::new(move |collection| collection.into_iter().take(n).collect())
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
