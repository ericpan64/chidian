use serde_json::Value;
use std::error::Error;

use crate::{JsonContainer, Chainable};
use crate::mapper::MappingContext;

/// Get a value from a JSON object using a selector.
///
/// This function traverses a `serde_json::Value` using a selector string 
/// and returns the (possibly-transformed) result.
/// 
/// The selector string syntax is as follows:
/// - `"users"` - select a field from an object
/// - `"[0]"` - select an array element by index
/// - `"[-1]"` - select the last element of an array using negative index
/// - `"[start:end]"` - select a slice of an array
/// - `"[*]"` - select all elements of an array
/// - `"(field1, field2)"` - select multiple fields as a tuple (returns array)
/// - `"users[0].name"` - chain selectors to traverse nested structures
///
/// # Arguments
/// * `source` - The source JSON object to traverse
/// * `key_str` - The selector string to parse
/// * `ops` - A slice of transforms to apply to the selected value
///
/// # Returns
/// * `Result<Value>` - The selected value, potentially transformed, or an error
///
/// # Example
/// ```
// / use chidian_core::dicts::{get, Value};
// / use serde_json::json;
// /
// / let data = json!({
// /     "users": [
// /         {"name": "Alice", "age": 30},
// /         {"name": "Bob", "age": 25}
// /     ]
// / });
// /
// / let result1 = get(&data, "users[0].name", None).unwrap();
// / let result2 = get(&data, "users[0].(name, age)", None).unwrap();
// / 
// / assert_eq!(result1, json!("Alice"));
// / assert_eq!(result2, json!(["Alice", 30]));
/// ```
pub fn get(source: JsonContainer, key_str: &str, on_success: Option<Box <dyn Chainable>>) -> Result<MappingContext, Box<dyn Error>> {
    // TODO: implement this in conjunction with the `dsl_parser`
    // Parse `key_str` into DSL parser components
    // Grab into the data based on the parsed key components
    //   for each actionable item:
    //       try the nested grab. If successful, keep going
    //       Else if unsuccessful, note current key and return appropriate Error (key_str_related) result with reason
    // If `on_success` is defined:
    //   for each Chainable function in `on_success`:
    //      Call `.run` for that function. If it returns an `Ok`, then keep going
    //      Else if unsuccessful, note current key and return appropriate Error (on_success_related) result with reason
    // At this point, this means everything ran successfully! Return the final result

    // ... dummy placeholder
    Ok(MappingContext::new(Value::Null))
}