use serde_json::Value;
use std::error::Error;

use crate::{JsonContainer, Chainable, Tuple};
use crate::mapper::{MappingContext, is_strict_mode, mark_missing_key_accessed};
use super::dsl_parser::{parse_get_expr, GetActionableUnit, IndexOp, GetExpr};

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
    // Parse the key string using the DSL parser
    let (_, parsed) = parse_get_expr(key_str)
        .map_err(|e| format!("Failed to parse key '{}': {}", key_str, e))?;
    
    // Start with the source data
    let mut current_value = Value::from(source);
    
    // Process each unit in the parsed expression
    for unit in &parsed.expr.units {
        current_value = process_unit(&current_value, unit)?;
    }
    
    // Create the result context
    let mut result_context = MappingContext::new(current_value);
    
    // Apply the chainable operation if provided
    if let Some(chainable) = on_success {
        result_context = chainable.run(result_context)?;
    }
    
    Ok(result_context)
}

fn process_unit(value: &Value, unit: &GetActionableUnit) -> Result<Value, Box<dyn Error>> {
    match unit {
        GetActionableUnit::Single { name, index } => {
            let mut result = get_field(value, name)?;
            if let Some(idx_op) = index {
                result = apply_index_op(&result, idx_op)?;
            }
            Ok(result)
        },
        GetActionableUnit::ListOp { name, index } => {
            let target = if let Some(field_name) = name {
                get_field(value, field_name)?
            } else {
                value.clone()
            };
            apply_index_op(&target, index)
        },
        GetActionableUnit::Tuple(exprs) => {
            process_tuple(value, exprs)
        }
    }
}

fn process_tuple(value: &Value, exprs: &[GetExpr]) -> Result<Value, Box<dyn Error>> {
    match value {
        Value::Array(arr) => {
            // For arrays, apply the tuple to each element recursively
            let mut results = Vec::new();
            for item in arr {
                results.push(process_tuple(item, exprs)?);
            }
            // Return a Tuple wrapper instead of a plain array
            let tuple = Tuple::new(results);
            Ok(tuple.to_value())
        },
        _ => {
            // For non-arrays, process each tuple field on the single value
            let mut results = Vec::new();
            for expr in exprs {
                let mut current = value.clone();
                for sub_unit in &expr.units {
                    current = process_unit(&current, sub_unit).unwrap_or(Value::Null);
                }
                results.push(current);
            }
            // Return a Tuple wrapper instead of a plain array
            let tuple = Tuple::new(results);
            Ok(tuple.to_value())
        }
    }
}

fn get_field(value: &Value, field_name: &str) -> Result<Value, Box<dyn Error>> {
    match value {
        Value::Object(obj) => {
            match obj.get(field_name) {
                Some(val) => Ok(val.clone()),
                None => {
                    // Mark that a missing key was accessed if we're in strict mode
                    if is_strict_mode() {
                        mark_missing_key_accessed();
                    }
                    Err(format!("Field '{}' not found", field_name).into())
                }
            }
        },
        Value::Array(arr) => {
            // For arrays, apply the field access to each element
            let results: Vec<Value> = arr.iter()
                .map(|item| get_field(item, field_name).unwrap_or(Value::Null))
                .collect();
            // Return a Tuple wrapper instead of a plain array
            let tuple = Tuple::new(results);
            Ok(tuple.to_value())
        },
        _ => Err(format!("Cannot access field '{}' on non-object/non-array value", field_name).into())
    }
}

fn apply_index_op(value: &Value, index_op: &IndexOp) -> Result<Value, Box<dyn Error>> {
    match value {
        Value::Array(arr) => {
            match index_op {
                IndexOp::Single(idx) => {
                    let len = arr.len() as i32;
                    let actual_idx = if *idx < 0 {
                        len + idx
                    } else {
                        *idx
                    };
                    
                    if actual_idx >= 0 && (actual_idx as usize) < arr.len() {
                        Ok(arr[actual_idx as usize].clone())
                    } else {
                        Err(format!("Index {} out of bounds for array of length {}", idx, len).into())
                    }
                },
                IndexOp::Slice(start, end) => {
                    let len = arr.len() as i32;
                    let start_idx = start.unwrap_or(0);
                    let end_idx = end.unwrap_or(len);
                    
                    let actual_start = if start_idx < 0 { len + start_idx } else { start_idx };
                    let actual_end = if end_idx < 0 { len + end_idx } else { end_idx };
                    
                    let start_bound = (actual_start.max(0) as usize).min(arr.len());
                    let end_bound = (actual_end.max(0) as usize).min(arr.len());
                    
                    if start_bound <= end_bound {
                        Ok(Value::Array(arr[start_bound..end_bound].to_vec()))
                    } else {
                        Ok(Value::Array(vec![]))
                    }
                },
                IndexOp::Star => {
                    // Return all elements
                    Ok(Value::Array(arr.clone()))
                }
            }
        },
        _ => Err("Cannot apply index operation to non-array value".into())
    }
}