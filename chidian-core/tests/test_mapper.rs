use std::collections::HashMap;
use serde_json::{json, Value};
use std::error::Error;

use chidian_core::{Chainable, DROP, KEEP, JsonContainer};
use chidian_core::dicts::get;
use chidian_core::mapper::{Mapper, MappingContext, MapperConfig};

// Helper to create a simple data structure similar to the Python one
fn simple_data() -> Value {
    json!({
        "data": {
            "patient": {
                "id": "123",
                "name": "Test Patient"
            }
        }
    })
}

#[test]
fn test_drop() {
    // Debug DROP serialization
    let drop_val = DROP::ThisObject;
    let json_val = serde_json::to_value(drop_val).unwrap();
    println!("DEBUG: DROP::ThisObject serializes to: {:?}", json_val);
    
    let source = simple_data();
    
    struct DropMapping;
    impl Chainable for DropMapping {
        fn name(&self) -> String {
            "drop_mapping".to_string()
        }
        
        fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let d = context.data.clone();
            let container = JsonContainer::try_from(d)?;
            let result = json!({
                "CASE_parent_keep": {
                    "CASE_curr_drop": {
                        "a": DROP::ThisObject,
                        "b": "someValue"
                    },
                    "CASE_curr_keep": {
                        "id": get(container, "data.patient.id", None).unwrap().data
                    }
                },
                "CASE_list": [DROP::ThisObject],
                "CASE_list_of_objects": [
                    {"a": DROP::Parent, "b": "someValue"},
                    {"a": "someValue", "b": "someValue"}
                ]
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper = Mapper::new(&DropMapping).with_config(config);
    
    let res = mapper.map(source).unwrap();
    
    assert_eq!(res, json!({
        "CASE_parent_keep": {
            "CASE_curr_keep": {
                "id": "123"
            }
        }
    }));
}

#[test]
#[should_panic(expected = "Cannot DROP: Not enough container depth in ancestry")]
fn test_drop_out_of_bounds() {
    let source = json!({});
    
    struct OutOfBoundsMapping;
    impl Chainable for OutOfBoundsMapping {
        fn name(&self) -> String {
            "out_of_bounds_mapping".to_string()
        }
        
        fn run(&self, _context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let result = json!({
                "parent": {
                    "CASE_no_grandparent": DROP::GreatGrandparent
                }
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper = Mapper::new(&OutOfBoundsMapping).with_config(config);
    let _ = mapper.map(source).unwrap(); // Should panic
}

#[test]
fn test_drop_exact_level() {
    let source = json!({});
    
    struct ExactLevelMapping;
    impl Chainable for ExactLevelMapping {
        fn name(&self) -> String {
            "exact_level_mapping".to_string()
        }
        
        fn run(&self, _context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let result = json!({
                "parent": {
                    "CASE_has_parent_object": DROP::Parent
                },
                "other_data": 123
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper = Mapper::new(&ExactLevelMapping).with_config(config);
    let res = mapper.map(source).unwrap();
    
    assert_eq!(res, json!({}));
}

#[test]
fn test_drop_repeat() {
    let source = json!({});
    
    struct RepeatMapping;
    impl Chainable for RepeatMapping {
        fn name(&self) -> String {
            "repeat_mapping".to_string()
        }
        
        fn run(&self, _context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let result = json!({
                "dropped_direct": [DROP::ThisObject, DROP::ThisObject],
                "also_dropped": [{"parent_key": DROP::Parent}, DROP::ThisObject],
                "partially_dropped": [
                    "first_kept",
                    {"second_dropped": DROP::ThisObject},
                    "third_kept",
                    {"fourth_dropped": DROP::ThisObject}
                ]
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper = Mapper::new(&RepeatMapping).with_config(config);
    let res = mapper.map(source).unwrap();
    
    assert_eq!(res, json!({
        "partially_dropped": ["first_kept", "third_kept"]
    }));
}

#[test]
fn test_keep_empty_value() {
    let source = json!({});
    
    struct KeepEmptyMapping;
    impl Chainable for KeepEmptyMapping {
        fn name(&self) -> String {
            "keep_empty_mapping".to_string()
        }
        
        fn run(&self, _context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let result = json!({
                "empty_vals": [
                    KEEP::new(json!({})),
                    KEEP::new(json!([])),
                    KEEP::new(json!("")),
                    KEEP::new(json!(null))
                ],
                "nested_vals": {
                    "dict": KEEP::new(json!({})),
                    "list": KEEP::new(json!([])),
                    "str": KEEP::new(json!("")),
                    "none": KEEP::new(json!(null)),
                    "other_static_val": "Abc"
                },
                "static_val": "Def",
                "empty_list": KEEP::new(json!([])),
                "removed_empty_list": []
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper = Mapper::new(&KeepEmptyMapping).with_config(config);
    let res = mapper.map(source).unwrap();
    
    // Verify KEEP functionality 
    assert_eq!(res, json!({
        "empty_vals": [{}, [], "", null],
        "nested_vals": {
            "dict": {},
            "list": [],
            "str": "",
            "none": null,
            "other_static_val": "Abc"
        },
        "static_val": "Def",
        "empty_list": []
    }));
}

#[test]
fn test_strict() {
    let source = simple_data();
    
    struct StrictMapping;
    impl Chainable for StrictMapping {
        fn name(&self) -> String {
            "strict_mapping".to_string()
        }
        
        fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let d = context.data.clone();
            let container = JsonContainer::try_from(d)?;
            let result = json!({
                "CASE_parent_keep": {
                    "CASE_curr_drop": {
                        "a": DROP::ThisObject,
                        "b": "someValue"
                    },
                    "CASE_curr_keep": {
                        "id": get(container.clone(), "data.patient.id", None).unwrap().data
                    }
                },
                "CASE_missing": get(container, "key.nope.not.there", None).map(|ctx| ctx.data).unwrap_or(Value::Null)
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    // Test strict mode
    let strict_config = MapperConfig::new(true, true, false, HashMap::new());
    let mapper_strict = Mapper::new(&StrictMapping).with_config(strict_config);
    
    let strict_result = mapper_strict.map(source.clone());
    assert!(strict_result.is_err());
    
    // Test non-strict mode
    let non_strict_config = MapperConfig::new(true, false, false, HashMap::new());
    let mapper_non_strict = Mapper::new(&StrictMapping).with_config(non_strict_config);
    
    let non_strict_result = mapper_non_strict.map(source).unwrap();
    assert_eq!(non_strict_result, json!({
        "CASE_parent_keep": {
            "CASE_curr_keep": {
                "id": "123"
            }
        }
    }));
}

#[test]
fn test_strict_deliberate_none() {
    let source = json!({
        "has_None": null,
        "nested_None": {
            "has_None": null,
            "has_value": "value"
        },
        "nested_list_None": {
            "some_list": [
                {"has_None": null},
                "value",
                null
            ]
        }
    });
    
    struct DeliberateNoneMapping;
    impl Chainable for DeliberateNoneMapping {
        fn name(&self) -> String {
            "deliberate_none_mapping".to_string()
        }
        
        fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let d = context.data.clone();
            let container = JsonContainer::try_from(d)?;
            let result = json!({
                "CASE_keep_None": get(container.clone(), "has_None", None).map(|ctx| ctx.data).unwrap_or(Value::Null),
                "CASE_keep_None_nested": get(container.clone(), "nested_None.has_None", None).map(|ctx| ctx.data).unwrap_or(Value::Null),
                "CASE_keep_None_list": get(container.clone(), "nested_list_None.some_list[-1]", None).map(|ctx| ctx.data).unwrap_or(Value::Null),
                "CASE_keep_None_list_nested": get(container, "nested_list_None.some_list[0].has_None", None).map(|ctx| ctx.data).unwrap_or(Value::Null)
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    // Test with strict mode
    let config = MapperConfig::new(false, true, false, HashMap::new());
    let mapper = Mapper::new(&DeliberateNoneMapping).with_config(config);
    
    let res = mapper.map(source.clone()).unwrap();
    assert_eq!(res, json!({
        "CASE_keep_None": null,
        "CASE_keep_None_nested": null,
        "CASE_keep_None_list": null,
        "CASE_keep_None_list_nested": null
    }));
    
    // Test error case
    struct ErrorMapping;
    impl Chainable for ErrorMapping {
        fn name(&self) -> String {
            "error_mapping".to_string()
        }
        
        fn run(&self, context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
            let d = context.data.clone();
            let container = JsonContainer::try_from(d)?;
            let result = json!({
                "CASE_keep_None": get(container.clone(), "has_None", None).map(|ctx| ctx.data).unwrap_or(Value::Null),
                "CASE_throw_err": get(container, "key.not.found", None)?.data
            });
            
            Ok(MappingContext::new(result))
        }
    }
    
    let err_config = MapperConfig::new(false, true, false, HashMap::new());
    let err_mapper = Mapper::new(&ErrorMapping).with_config(err_config);
    
    let err_res = err_mapper.map(source);
    assert!(err_res.is_err());
}
