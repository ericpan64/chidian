mod parser;
mod selector;
mod transform;
mod cache;

pub use selector::{Selector, PathNode, SelectorError, Result};
pub use transform::{Transform, chain_transforms};
pub use serde_json::Value;
pub type Object = serde_json::Map<String, Value>;

/// Get a value from a JSON object using a selector.
///
/// This function traverses a `serde_json::Value` using a selector string 
/// and returns the (possibly-transformed) result.
/// 
/// The selector string can optionally begin with a dot. The following syntax is supported:
/// - `"users"` or `".users"` - select a field from an object
/// - `"[0]"` - select an array element by index
/// - `"[-1]"` - select the last element of an array using negative index
/// - `"[start:end]"` - select a slice of an array
/// - `"[*]"` - select all elements of an array
/// - `"users[0].name"` - chain selectors to traverse nested structures
///
/// # Arguments
/// * `src` - The source JSON object to traverse
/// * `sel_str` - The selector string to parse
/// * `ops` - A slice of transforms to apply to the selected value
///
/// # Returns
/// * `Result<Value>` - The selected value, potentially transformed, or an error
///
/// # Example
/// ```
/// use chidian_core::{get, Value};
/// use serde_json::json;
///
/// let data = json!({
///     "users": [
///         {"name": "Alice", "age": 30},
///         {"name": "Bob", "age": 25}
///     ]
/// });
///
/// // With leading dot (traditional style)
/// let result1 = get(&data, ".users[0].name", &[]).unwrap();
/// 
/// // Without leading dot (new style)
/// let result2 = get(&data, "users[0].name", &[]).unwrap();
/// 
/// assert_eq!(result1, json!("Alice"));
/// assert_eq!(result2, json!("Alice"));
/// ```
pub fn get(src: &Value, sel_str: &str, ops: &[Box<dyn Transform>]) -> Result<Value> {
    let selector = cache::get_cached_selector(sel_str)?;
    get_selector(src, &selector, ops)
}

/// Get a value from a JSON object using a parsed selector.
///
/// This function traverses a `serde_json::Value` using a parsed selector 
/// and returns the (possibly-transformed) result.
///
/// # Arguments
/// * `src` - The source JSON object to traverse
/// * `sel` - The selector that defines the path to traverse
/// * `ops` - A slice of transforms to apply to the selected value
///
/// # Returns
/// * `Result<Value>` - The selected value, potentially transformed, or an error
///
/// # Example
/// ```
/// use chidian_core::{get_selector, Selector, Value};
/// use serde_json::json;
///
/// let data = json!({
///     "users": [
///         {"name": "Alice", "age": 30},
///         {"name": "Bob", "age": 25}
///     ]
/// });
///
/// let selector = Selector::parse("users[0].name").unwrap();
/// let result = get_selector(&data, &selector, &[]).unwrap();
/// assert_eq!(result, json!("Alice"));
/// ```
pub fn get_selector(src: &Value, sel: &Selector, ops: &[Box<dyn Transform>]) -> Result<Value> {
    // First select the data
    let selected = sel.evaluate(src)?;
    
    // Then apply transforms in sequence if there are any
    let transformed = transform::chain_transforms(selected, ops);
    
    Ok(transformed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_get_function() -> Result<()> {
        let data = json!({
            "users": [
                {"name": "Alice", "age": 30},
                {"name": "Bob", "age": 25}
            ],
            "config": {
                "version": "1.0",
                "features": ["auth", "api", "ui"]
            }
        });

        // Test simple key access with leading dot
        let selector = Selector::parse(".config.version")?;
        let result = get_selector(&data, &selector, &[])?;
        assert_eq!(result, json!("1.0"));

        // Test simple key access without leading dot
        let selector = Selector::parse("config.version")?;
        let result = get_selector(&data, &selector, &[])?;
        assert_eq!(result, json!("1.0"));

        // Test array index
        let selector = Selector::parse("users[1].name")?;
        let result = get_selector(&data, &selector, &[])?;
        assert_eq!(result, json!("Bob"));

        // Test array slice
        let selector = Selector::parse("config.features[0:2]")?;
        let result = get_selector(&data, &selector, &[])?;
        assert_eq!(result, json!(["auth", "api"]));

        // Test using get
        let result = get(&data, "users[0].age", &[])?;
        assert_eq!(result, json!(30));
        
        Ok(())
    }

    // Testing errors
    #[test]
    fn test_get_errors() {
        let data = json!({
            "user": {"name": "John"}
        });

        // Key not found
        let result = get(&data, "user.age", &[]);
        assert!(result.is_err());

        // Invalid selector
        let result = get(&data, "..invalid", &[]);
        assert!(result.is_err());
    }
}
