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

/// A DeleteRelativeObjectPlaceholder (DROP) indicates which object relative 
/// to the current value should be dropped. An "object" in this context
/// refers to a JSON container (object/map or array).
///
/// Examples:
///
/// ```
/// // Object structure:
/// // {   <- Grandparent (rel to _value)
/// //     'A': {   <- Parent (rel to _value)
/// //         'B': {      <- This Object (rel to _value)
/// //             'C': _value
/// //         }
/// //     }
/// // }
///
/// // Array structure:
/// // {   <- Grandparent (rel to _value1 and _value2)
/// //     'A': [  <- Parent (rel to _value1 and _value2)
/// //         {       <- This Object (rel to _value1)
/// //             'B': _value1
/// //         },
/// //         {       <- This Object (rel to _value2)
/// //             'B': _value2
/// //         }
/// //     ]
/// // }
/// ```
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DROP {
    /// Drop the object that directly contains the current value (-1)
    ThisObject,
    /// Drop the parent object that contains ThisObject (-2)
    Parent,
    /// Drop the grandparent object that contains Parent (-3)
    Grandparent,
    /// Drop the great-grandparent object that contains Grandparent (-4)
    GreatGrandparent,
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

/// A value wrapped in a KeepEmptyEntityPlaceholder (KEEP) object should be ignored by the Mapper when removing empty values.
/// 
/// This preserves values that would normally be considered "empty" and removed.
/// Partial keeping is not supported (i.e., a KEEP object within an object to be DROP-ed).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KEEP {
    /// The value to be preserved even if it would be considered "empty"
    pub value: Value,
}

/// Checks if a JSON value has "content" (is not empty).
/// 
/// A value is considered to have content if:
/// - It is not null
/// - If it's a collection (object/array), it has at least one item with content
/// - Empty strings, empty objects, and empty arrays are considered to not have content
pub fn has_content(value: &Value) -> bool {
    if value.is_null() {
        return false;
    }
    
    if let Some(obj) = value.as_object() {
        return !obj.is_empty() && obj.values().any(has_content);
    }
    
    if let Some(arr) = value.as_array() {
        return !arr.is_empty() && arr.iter().any(has_content);
    }
    
    if let Some(s) = value.as_str() {
        return !s.is_empty();
    }
    
    // Numbers, booleans always have content
    true
}

/// Recursively removes "empty" values from a JSON structure.
/// 
/// Empty values include:
/// - null
/// - Empty strings
/// - Empty objects
/// - Empty arrays
/// - Objects/arrays that only contain empty values
/// 
/// Values wrapped in KEEP will be preserved regardless of emptiness.
pub fn remove_empty_values(value: Value) -> Value {
    // Handle KEEP-wrapped values
    if let Ok(obj) = serde_json::from_value::<KEEP>(value.clone()) {
        return obj.value;
    }
    
    match value {
        Value::Object(map) => {
            let mut result = serde_json::Map::new();
            for (k, v) in map {
                let processed = remove_empty_values(v);
                if has_content(&processed) {
                    result.insert(k, processed);
                }
            }
            Value::Object(result)
        },
        Value::Array(arr) => {
            let result: Vec<Value> = arr
                .into_iter()
                .map(remove_empty_values)
                .filter(has_content)
                .collect();
            Value::Array(result)
        },
        // Other primitive values are returned as-is
        _ => value,
    }
}

/// Recursively flattens nested arrays in a JSON value.
/// 
/// This also unwraps `KEEP` values during flattening.
/// 
/// Example:
/// ```
/// // Given: [[1, 2, 3], [4, 5, 6], null, [7, 8, 9]]
/// // Returns: [1, 2, 3, 4, 5, 6, 7, 8, 9]
/// ```
pub fn flatten_sequence(value: Value) -> Value {
    // Handle KEEP-wrapped values
    if let Ok(obj) = serde_json::from_value::<KEEP>(value.clone()) {
        return obj.value;
    }
    
    if let Value::Array(arr) = value {
        let mut result = Vec::new();
        for item in arr {
            match item {
                Value::Array(_) => {
                    // Recursively flatten nested arrays
                    if let Value::Array(flattened) = flatten_sequence(item) {
                        result.extend(flattened);
                    }
                },
                Value::Null => {
                    // Skip null values
                },
                _ => {
                    // Keep other non-array values
                    result.push(item);
                }
            }
        }
        Value::Array(result)
    } else {
        // Non-array values are returned as-is
        value
    }
}
