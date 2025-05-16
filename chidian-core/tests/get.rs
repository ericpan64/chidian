use chidian_core::{get, get_selector, Selector};
use serde_json::json;

#[test]
fn test_get_basic() {
    let data = json!({
        "user": {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 30,
            "active": true,
            "accounts": ["github", "twitter", "linkedin"]
        },
        "settings": {
            "theme": "dark",
            "notifications": true
        }
    });

    // Test simple key access
    let result = get(&data, "user.name", &[]).unwrap();
    assert_eq!(result, json!("John Doe"));

    // Test array index
    let result = get(&data, "user.accounts[1]", &[]).unwrap();
    assert_eq!(result, json!("twitter"));

    // Test negative index
    let result = get(&data, "user.accounts[-1]", &[]).unwrap();
    assert_eq!(result, json!("linkedin"));

    // Test boolean value
    let result = get(&data, "user.active", &[]).unwrap();
    assert_eq!(result, json!(true));

    // Test number value
    let result = get(&data, "user.age", &[]).unwrap();
    assert_eq!(result, json!(30));
}

#[test]
fn test_array_operations() {
    let data = json!({
        "items": [
            {"id": 1, "name": "Item 1", "tags": ["new", "featured"]},
            {"id": 2, "name": "Item 2", "tags": ["sale"]},
            {"id": 3, "name": "Item 3", "tags": ["new", "sale"]},
            {"id": 4, "name": "Item 4", "tags": []}
        ]
    });

    // Test wildcard
    let result = get(&data, "items[*].id", &[]).unwrap();
    assert_eq!(result, json!([1, 2, 3, 4]));

    // Test slice
    let result = get(&data, "items[1:3].name", &[]).unwrap();
    assert_eq!(result, json!(["Item 2", "Item 3"]));

    // Test empty slice end
    let result = get(&data, "items[2:].id", &[]).unwrap();
    assert_eq!(result, json!([3, 4]));

    // Test empty slice start
    let result = get(&data, "items[:2].id", &[]).unwrap();
    assert_eq!(result, json!([1, 2]));

    // Test nested wildcard
    let result = get(&data, "items[*].tags[0]", &[]).unwrap();
    // Note: Item 4 has empty tags, so no result for it
    assert_eq!(result, json!(["new", "sale", "new"]));
}

#[test]
fn test_path_not_found() {
    let data = json!({"user": {"name": "John"}});

    // Key doesn't exist
    let result = get(&data, "user.email", &[]);
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("not found"));

    // Path doesn't exist at all
    let result = get(&data, "settings.theme", &[]);
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("not found"));
}

#[test]
fn test_type_mismatch() {
    let data = json!({"name": "John", "age": 30});

    // Try to access a property on a non-object
    let result = get(&data, "age.value", &[]);
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("mismatch"));

    // Try to access an index on a non-array
    let result = get(&data, "name[0]", &[]);
    assert!(result.is_err());
    assert!(result.unwrap_err().to_string().contains("mismatch"));
}

#[test]
fn test_selector_reuse() {
    let data1 = json!({"user": {"name": "John"}});
    let data2 = json!({"user": {"name": "Jane"}});

    // Parse selector once and reuse
    let selector = Selector::parse("user.name").unwrap();
    
    let result1 = get_selector(&data1, &selector, &[]).unwrap();
    let result2 = get_selector(&data2, &selector, &[]).unwrap();

    assert_eq!(result1, json!("John"));
    assert_eq!(result2, json!("Jane"));
} 