use chidian_core::{get, get_selector, Selector};
use serde_json::json;

/// Test fixtures containing reusable JSON data structures for tests
mod fixtures {
    use serde_json::json;

    /// Basic user and settings data
    pub fn get_basic_data() -> serde_json::Value {
        json!({
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
        })
    }

    /// Item collection with various tags
    pub fn get_items_data() -> serde_json::Value {
        json!({
            "items": [
                {"id": 1, "name": "Item 1", "tags": ["new", "featured"]},
                {"id": 2, "name": "Item 2", "tags": ["sale"]},
                {"id": 3, "name": "Item 3", "tags": ["new", "sale"]},
                {"id": 4, "name": "Item 4", "tags": []}
            ]
        })
    }

    /// Simple object for error testing
    pub fn get_simple_data() -> serde_json::Value {
        json!({"user": {"name": "John"}})
    }

    /// Type mismatch test data
    pub fn get_type_mismatch_data() -> serde_json::Value {
        json!({"name": "John", "age": 30})
    }

    /// Complex address and name data from README example
    pub fn get_complex_address_data() -> serde_json::Value {
        json!({
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
        })
    }

    /// Expected transformed data for README example
    pub fn get_expected_transformed_data() -> serde_json::Value {
        json!({
            "full_name": "Bob S Figgens Sr.",
            "current_address": "123 Privet Drive\nLittle Whinging\nSurrey\nAB12 3CD\nUnited Kingdom",
            "last_previous_address": "12 Grimmauld Place\nIslington\nLondon\nN1 3AX\nUnited Kingdom"
        })
    }
}

#[test]
fn test_get_basic() {
    let data = fixtures::get_basic_data();

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
    let data = fixtures::get_items_data();

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
    let data = fixtures::get_simple_data();

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
    let data = fixtures::get_type_mismatch_data();

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

#[test]
fn test_complex_address_paths() {
    let data = fixtures::get_complex_address_data();
    
    // Test accessing first name
    let result = get(&data, "name.first", &[]).unwrap();
    assert_eq!(result, json!("Bob"));
    
    // Test accessing middle initial
    let result = get(&data, "name.given[0]", &[]).unwrap();
    assert_eq!(result, json!("S"));
    
    // Test accessing current street address first line
    let result = get(&data, "address.current.street[0]", &[]).unwrap();
    assert_eq!(result, json!("123 Privet Drive"));
    
    // Test accessing last previous address city
    let result = get(&data, "address.previous[-1].city", &[]).unwrap();
    assert_eq!(result, json!("London"));
} 