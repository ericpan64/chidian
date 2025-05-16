use std::sync::Arc;
use serde_json::Value;
use thiserror::Error;

use crate::parser::parse_selector;

#[derive(Debug, Clone, PartialEq)]
pub enum PathNode {
    Key(String),           // .key
    Index(isize),          // [0] / [-1]
    Wildcard,              // [*]
    Slice(Option<isize>, Option<isize>), // [start:end]
}

#[derive(Debug, Clone)]
pub struct Selector {
    nodes: Vec<PathNode>,
}

#[derive(Error, Debug)]
pub enum SelectorError {
    #[error("Parse error: {0}")]
    ParseError(String),
    
    #[error("Path not found: {0}")]
    PathNotFound(String),
    
    #[error("Invalid index: {0}")]
    InvalidIndex(String),
    
    #[error("Type mismatch: expected {expected}, found {found}")]
    TypeMismatch { expected: String, found: String },
}

pub type Result<T> = std::result::Result<T, SelectorError>;

impl Selector {
    /// Create a new Selector from a vector of PathNodes
    pub fn new(nodes: Vec<PathNode>) -> Self {
        Selector { nodes }
    }
    
    /// Parse a selector string into a Selector
    pub fn parse(input: &str) -> Result<Arc<Self>> {
        match parse_selector(input) {
            Ok(nodes) => Ok(Arc::new(Selector::new(nodes))),
            Err(e) => Err(SelectorError::ParseError(e)),
        }
    }
    
    /// Evaluate the selector against a JSON value
    pub fn evaluate(&self, value: &Value) -> Result<Value> {
        self.eval_path(&self.nodes, value)
    }
    
    /// Recursive helper to evaluate a path against a JSON value
    fn eval_path(&self, path: &[PathNode], current: &Value) -> Result<Value> {
        // Base case - empty path means we've reached destination
        if path.is_empty() {
            return Ok(current.clone());
        }
        
        match &path[0] {
            PathNode::Key(key) => {
                if let Value::Object(map) = current {
                    if let Some(next) = map.get(key) {
                        return self.eval_path(&path[1..], next);
                    }
                    return Err(SelectorError::PathNotFound(format!("Key '{}' not found", key)));
                }
                Err(SelectorError::TypeMismatch { 
                    expected: "object".to_string(), 
                    found: value_type_name(current),
                })
            },
            PathNode::Index(idx) => {
                if let Value::Array(arr) = current {
                    let idx = if *idx < 0 {
                        arr.len().checked_sub(idx.unsigned_abs() as usize)
                    } else {
                        Some(*idx as usize)
                    };
                    
                    if let Some(i) = idx {
                        if i < arr.len() {
                            return self.eval_path(&path[1..], &arr[i]);
                        }
                    }
                    return Err(SelectorError::InvalidIndex(format!("Index {:?} out of bounds", idx)));
                }
                Err(SelectorError::TypeMismatch { 
                    expected: "array".to_string(), 
                    found: value_type_name(current),
                })
            },
            PathNode::Wildcard => {
                if let Value::Array(arr) = current {
                    let mut results = Vec::with_capacity(arr.len());
                    for item in arr {
                        match self.eval_path(&path[1..], item) {
                            Ok(value) => results.push(value),
                            // Skip errors in wildcard matches
                            Err(_) => continue,
                        }
                    }
                    Ok(Value::Array(results))
                } else {
                    Err(SelectorError::TypeMismatch { 
                        expected: "array".to_string(), 
                        found: value_type_name(current),
                    })
                }
            },
            PathNode::Slice(start, end) => {
                if let Value::Array(arr) = current {
                    // Convert slice bounds to Rust ranges
                    let start_idx = start.map(|i| {
                        if i < 0 {
                            arr.len().saturating_sub(i.unsigned_abs() as usize)
                        } else {
                            i as usize
                        }
                    }).unwrap_or(0);
                    
                    let end_idx = end.map(|i| {
                        if i < 0 {
                            arr.len().saturating_sub(i.unsigned_abs() as usize)
                        } else {
                            i as usize
                        }
                    }).unwrap_or(arr.len());
                    
                    let mut results = Vec::new();
                    for item in arr.iter().skip(start_idx.min(arr.len())).take(end_idx.saturating_sub(start_idx)) {
                        match self.eval_path(&path[1..], item) {
                            Ok(value) => results.push(value),
                            // Skip errors in slice items
                            Err(_) => continue,
                        }
                    }
                    Ok(Value::Array(results))
                } else {
                    Err(SelectorError::TypeMismatch { 
                        expected: "array".to_string(), 
                        found: value_type_name(current),
                    })
                }
            },
        }
    }
}

/// Helper to get the type name of a JSON value
fn value_type_name(value: &Value) -> String {
    match value {
        Value::Null => "null".to_string(),
        Value::Bool(_) => "boolean".to_string(),
        Value::Number(_) => "number".to_string(),
        Value::String(_) => "string".to_string(),
        Value::Array(_) => "array".to_string(),
        Value::Object(_) => "object".to_string(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_simple_key_access() {
        let data = json!({
            "user": {
                "name": "John",
                "age": 30
            }
        });
        
        let selector = Selector::parse(".user.name").unwrap();
        let result = selector.evaluate(&data).unwrap();
        assert_eq!(result, json!("John"));
    }

    #[test]
    fn test_array_index() {
        let data = json!({
            "items": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"}
            ]
        });
        
        let selector = Selector::parse(".items[1].name").unwrap();
        let result = selector.evaluate(&data).unwrap();
        assert_eq!(result, json!("Item 2"));
    }

    #[test]
    fn test_negative_index() {
        let data = json!({
            "items": ["a", "b", "c", "d"]
        });
        
        let selector = Selector::parse(".items[-1]").unwrap();
        let result = selector.evaluate(&data).unwrap();
        assert_eq!(result, json!("d"));
    }

    #[test]
    fn test_slice() {
        let data = json!({
            "items": ["a", "b", "c", "d", "e"]
        });
        
        let selector = Selector::parse(".items[1:3]").unwrap();
        let result = selector.evaluate(&data).unwrap();
        assert_eq!(result, json!(["b", "c"]));
    }

    #[test]
    fn test_wildcard() {
        let data = json!({
            "users": [
                {"name": "Alice", "age": 25},
                {"name": "Bob", "age": 30},
                {"name": "Charlie", "age": 35}
            ]
        });
        
        let selector = Selector::parse(".users[*].name").unwrap();
        let result = selector.evaluate(&data).unwrap();
        assert_eq!(result, json!(["Alice", "Bob", "Charlie"]));
    }

    #[test]
    fn test_error_key_not_found() {
        let data = json!({ "user": { "name": "John" } });
        let selector = Selector::parse(".user.email").unwrap();
        let result = selector.evaluate(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_error_index_out_of_bounds() {
        let data = json!({ "items": [1, 2, 3] });
        let selector = Selector::parse(".items[5]").unwrap();
        let result = selector.evaluate(&data);
        assert!(result.is_err());
    }

    #[test]
    fn test_error_type_mismatch() {
        let data = json!({ "name": "John" });
        let selector = Selector::parse(".name.first").unwrap();
        let result = selector.evaluate(&data);
        assert!(result.is_err());
        if let Err(SelectorError::TypeMismatch { expected, found }) = result {
            assert_eq!(expected, "object");
            assert_eq!(found, "string");
        } else {
            panic!("Expected TypeMismatch error");
        }
    }
} 