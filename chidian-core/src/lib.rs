use std::error::Error;
use serde_json::Value;
use serde::{Serialize, Deserialize};

pub mod mapper;
pub mod dicts;
pub mod partials;

/// Something that is `Chainable` is a pure function that accepts 1-parameter input and returns exactly 1-item output.
pub trait Chainable {
    /// Core logic for the function
    fn run(&self, source: mapper::MappingContext) -> Result<mapper::MappingContext, Box<dyn Error>>;
    /// The name of the function (can just use the function name as a string. Aim to be expressive and concise!)
    fn name(&self) -> String;
}

/// Represents JSON container types that can hold other values.
/// Limited to objects (key-value maps) and arrays, which are the only JSON types that can contain other values.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum JsonContainer {
    /// A JSON object (key-value map)
    Object(serde_json::Map<String, Value>),
    /// A JSON array (ordered list of values)
    Array(Vec<Value>),
}

impl From<JsonContainer> for Value {
    fn from(val: JsonContainer) -> Self {
        match val {
            JsonContainer::Object(map) => Value::Object(map),
            JsonContainer::Array(vec) => Value::Array(vec),
        }
    }
}

impl TryFrom<Value> for JsonContainer {
    type Error = Box<dyn Error>;

    fn try_from(value: Value) -> Result<Self, Self::Error> {
        match value {
            Value::Object(map) => Ok(JsonContainer::Object(map)),
            Value::Array(vec) => Ok(JsonContainer::Array(vec)),
            _ => Err("Value must be either an Object or Array container type".into()),
        }
    }
}
