use serde_json::{Value, json};
use std::error::Error;
use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use std::cell::RefCell;

use crate::{Chainable, DROP, KEEP};

// Thread-local storage to track if missing keys were accessed in strict mode
thread_local! {
    static STRICT_MODE_ENABLED: RefCell<bool> = RefCell::new(false);
    static MISSING_KEY_ACCESSED: RefCell<bool> = RefCell::new(false);
}

/// Set strict mode for the current thread
pub fn set_strict_mode(enabled: bool) {
    STRICT_MODE_ENABLED.with(|f| *f.borrow_mut() = enabled);
    MISSING_KEY_ACCESSED.with(|f| *f.borrow_mut() = false);
}

/// Check if strict mode is enabled
pub fn is_strict_mode() -> bool {
    STRICT_MODE_ENABLED.with(|f| *f.borrow())
}

/// Mark that a missing key was accessed
pub fn mark_missing_key_accessed() {
    MISSING_KEY_ACCESSED.with(|f| *f.borrow_mut() = true);
}

/// Check if a missing key was accessed
pub fn was_missing_key_accessed() -> bool {
    MISSING_KEY_ACCESSED.with(|f| *f.borrow())
}

/// The context for each step in the mapping process
pub struct MappingContext {
    /// The main data object
    pub data: Value,
    /// Supporting information (weakly-typed)
    pub metadata: Option<MappingContextMetadata>,
}

impl MappingContext {
    pub fn new(val: Value) -> Self {
        return MappingContext { data: val, metadata: None };
    }

    pub fn add_metadata(&mut self, metadata: MappingContextMetadata) -> () {
        self.metadata = Some(metadata);
    }
    
    /// Creates a clone of the data only, without the metadata
    pub fn clone_data(&self) -> Self {
        MappingContext {
            data: self.data.clone(),
            metadata: None,
        }
    }
}

#[derive(Serialize, Deserialize)]
pub struct MappingContextMetadata {
    /// A weakly-typed `Value::Object` with supporting metadata. Can be used when available
    other_sources: Option<Value>,
    /// A human-readable description of the current state of the mapping
    description: Option<String>,
    /// Log of steps - not serializable
    #[serde(skip)]
    run_log: Vec<MappingStep>,
}

impl MappingContextMetadata {
    pub fn new() -> Self {
        return MappingContextMetadata { other_sources: None, description: None, run_log: Vec::new() };
    }

    pub fn add_step(&mut self, step: MappingStep) -> () {
        self.run_log.push(step);
    }

    pub fn add_description(&mut self, description: String) -> () {
        self.description = Some(description);
    }

    pub fn add_other_source(&mut self, other_source: Value) -> () {
        self.other_sources = Some(other_source);
    }
}

pub struct MappingStep {
    /// The value before running the step
    pub source: Value,
    /// The value after running the step - not cloneable
    pub result: Result<Value, Box<dyn Error>>,
    /// The name of the Rust function that was called when running the step
    pub fn_name: String,
    /// A human-readable string with notes on this step
    pub notes: Option<String>,
}

impl MappingStep {
    pub fn new(source: Value, result: Result<Value, Box<dyn Error>>, called_fn: &dyn Chainable, notes: Option<String>) -> Self {
        let fn_name = format!("{:?}", called_fn.name());
        return MappingStep { source, result, fn_name, notes };
    }
}

/// A Mapper object that represents the configuration for a specific Json->Json (one-direction) transform.
///   This object can be imported / exported in a JSON format (for `mapping_fn`, the source code is read as a string)
pub struct Mapper<'a> {
    pub mapping_fn: &'a dyn Chainable,
    pub config: MapperConfig,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct MapperConfig {
    /// Whether to remove empty objects or arrays from the output
    pub remove_empty: bool,
    /// Whether to raise exection instead of returning None on missing keys
    ///   NOTE: This logic is handled in python/js implementations.
    ///   So in Rust, if this is enabled, have special type of Error 
    ///   that makes it clear that the error is due to missing keys + strict mode.
    pub strict: bool,
    /// Whether to cache the result of `get` into heavily nested data.
    ///   NOTE: This is likely only helpful for large and heavily nested data.
    ///   Otherwise, it will probably be slower due to overhead of managing the cache.
    pub use_nesting_cache: bool,
    /// A map of implementation notes. This is meant to be maintained by developers of data mappings.
    pub implementation_notes: HashMap<String, String>
}

impl MapperConfig {
    pub fn new(remove_empty: bool, strict: bool, use_nesting_cache: bool, implementation_notes: HashMap<String, String>) -> Self {
        return MapperConfig {
            remove_empty,
            strict,
            use_nesting_cache,
            implementation_notes,
        };
    }
}
 
impl<'a> Mapper<'a> {
    pub fn new(mapping_fn: &'a dyn Chainable) -> Self {
        return Mapper {
            mapping_fn,
            config: MapperConfig::new(true, false, false, HashMap::new()),
        };
    }

    pub fn with_config(mut self, config: MapperConfig) -> Self {
        self.config = config;
        self
    }
    
    /// Helper to detect DROP markers from JSON values
    fn detect_drop_marker(&self, value: &Value) -> Option<DROP> {
        // Try deserializing as DROP first
        if let Ok(drop_type) = serde_json::from_value::<DROP>(value.clone()) {
            println!("DEBUG: Found DROP via deserialization: {:?}", drop_type);
            return Some(drop_type);
        }
        
        // Try string-based detection (for when DROP serializes to strings)
        if let Some(s) = value.as_str() {
            let result = match s {
                "ThisObject" => Some(DROP::ThisObject),
                "Parent" => Some(DROP::Parent),
                "Grandparent" => Some(DROP::Grandparent),
                "GreatGrandparent" => Some(DROP::GreatGrandparent),
                _ => None,
            };
            if result.is_some() {
                println!("DEBUG: Found DROP via string detection: {:?} from string: {:?}", result, s);
            }
            result
        } else {
            None
        }
    }

    /// Helper to detect KEEP wrappers from JSON values
    fn detect_keep_wrapper(&self, value: &Value) -> Option<Value> {
        // Only try to deserialize as KEEP if it's an object that looks like a KEEP struct
        if let Some(obj) = value.as_object() {
            // Try object-based detection first (for when KEEP serializes to objects)
            if obj.len() == 1 && obj.contains_key("value") {
                return obj.get("value").cloned();
            }
            
            // Try deserializing as KEEP only if it looks like a KEEP object
            if let Ok(keep) = serde_json::from_value::<KEEP>(value.clone()) {
                return Some(keep.value);
            }
        }
        
        None
    }

    pub fn map(&self, data: Value) -> Result<Value, Box<dyn Error>> {
        // Set up strict mode for this mapping operation
        set_strict_mode(self.config.strict);
        
        // Create a new MappingContext
        let context = MappingContext::new(data);
        
        // Run the mapping function
        let result_context = self.mapping_fn.run(context)?;
        
        // Check if strict mode was violated
        if self.config.strict && was_missing_key_accessed() {
            return Err("Strict mode violation: missing key was accessed".into());
        }
        
        // Process the result to handle DROP and KEEP markers
        let processed = self.process_drops_and_keeps(result_context.data)?;
        
        // Remove empty values if configured
        let final_result = if self.config.remove_empty {
            self.remove_empty_values_with_keep(processed)
        } else {
            processed
        };
        
        Ok(final_result)
    }
    
    /// Process DROP markers and KEEP wrappers in the JSON structure
    fn process_drops_and_keeps(&self, value: Value) -> Result<Value, Box<dyn Error>> {
        let result = self.process_value_with_ancestry(value, &[])?;
        // If the root object gets dropped, return an empty object instead of null
        if result.is_null() {
            Ok(json!({}))
        } else {
            Ok(result)
        }
    }
    
    fn process_value_with_ancestry(&self, value: Value, ancestry: &[String]) -> Result<Value, Box<dyn Error>> {
        match value {
            Value::Object(map) => {
                let mut result = serde_json::Map::new();
                let mut should_drop_this_object = false;
                
                for (key, val) in map {
                    let mut new_ancestry = ancestry.to_vec();
                    new_ancestry.push(key.clone());
                    
                    // Check if this value is a KEEP wrapper first - preserve it but process the wrapped value
                    if let Some(keep_value) = self.detect_keep_wrapper(&val) {
                        // Process the wrapped value and mark it as KEEP for later preservation
                        let processed_wrapped = self.process_value_with_ancestry(keep_value, &new_ancestry)?;
                        // Mark this as a KEEP value so it's preserved during empty removal
                        let keep_marker = json!({"__KEEP_MARKER__": processed_wrapped});
                        result.insert(key, keep_marker);
                        continue;
                    }
                    
                    // Check if this value is a DROP marker
                    if let Some(drop_type) = self.detect_drop_marker(&val) {
                        let drop_depth = match drop_type {
                            DROP::ThisObject => 1,
                            DROP::Parent => 2,
                            DROP::Grandparent => 3,
                            DROP::GreatGrandparent => 4,
                        };
                        
                        if drop_depth > new_ancestry.len() {
                            return Err("Cannot DROP: Not enough container depth in ancestry".into());
                        }
                        
                        if drop_depth == 1 {
                            // Drop the current container (this object)
                            should_drop_this_object = true;
                            break;
                        } else {
                            // For deeper drops, propagate upward 
                            return Ok(json!({"__DROP_DEPTH__": drop_depth - 1}));
                        }
                    }
                    
                    // Process the value recursively
                    let processed_val = self.process_value_with_ancestry(val, &new_ancestry)?;
                    
                    // Check if the processed value signals a drop
                    if let Some(obj) = processed_val.as_object() {
                        if obj.contains_key("__DROP_MARKER__") {
                            // This object should be dropped - don't include it
                            continue;
                        } else if let Some(depth_val) = obj.get("__DROP_DEPTH__") {
                            if let Some(depth) = depth_val.as_u64() {
                                if depth == 1 {
                                    // This object should be dropped
                                    should_drop_this_object = true;
                                    break;
                                } else if depth > 1 {
                                    return Ok(json!({"__DROP_DEPTH__": depth - 1}));
                                }
                            }
                        }
                    }
                    
                    // Only exclude values that are drop signals, not regular null values
                    if processed_val.as_object().map_or(true, |o| !o.contains_key("__DROP_MARKER__") && !o.contains_key("__DROP_DEPTH__")) {
                        result.insert(key, processed_val);
                    }
                }
                
                if should_drop_this_object {
                    Ok(Value::Null)
                } else {
                    Ok(Value::Object(result))
                }
            },
            Value::Array(arr) => {
                let mut result = Vec::new();
                let mut should_drop_this_array = false;
                
                for (index, val) in arr.into_iter().enumerate() {
                    let mut new_ancestry = ancestry.to_vec();
                    new_ancestry.push(index.to_string());
                    
                    // Check if this value is a KEEP wrapper first - preserve it but process the wrapped value
                    if let Some(keep_value) = self.detect_keep_wrapper(&val) {
                        // Process the wrapped value and mark it as KEEP for later preservation
                        let processed_wrapped = self.process_value_with_ancestry(keep_value, &new_ancestry)?;
                        // Mark this as a KEEP value so it's preserved during empty removal
                        let keep_marker = json!({"__KEEP_MARKER__": processed_wrapped});
                        result.push(keep_marker);
                        continue;
                    }
                    
                    // Check if this value is a DROP marker
                    if let Some(drop_type) = self.detect_drop_marker(&val) {
                        let drop_depth = match drop_type {
                            DROP::ThisObject => 1,
                            DROP::Parent => 2,
                            DROP::Grandparent => 3,
                            DROP::GreatGrandparent => 4,
                        };
                        

                        
                        if drop_depth > new_ancestry.len() {
                            return Err("Cannot DROP: Not enough container depth in ancestry".into());
                        }
                        
                        if drop_depth == 1 {
                            // Drop the current container (this array)
                            should_drop_this_array = true;
                            break;
                        } else {
                            // For deeper drops, propagate upward
                            return Ok(json!({"__DROP_DEPTH__": drop_depth - 1}));
                        }
                    }
                    
                    // Process the value recursively
                    let processed_val = self.process_value_with_ancestry(val, &new_ancestry)?;
                    
                    // Check if the processed value signals a drop
                    if let Some(obj) = processed_val.as_object() {
                        if obj.contains_key("__DROP_MARKER__") {
                            // Skip this item - it should be dropped
                            continue;
                        } else if let Some(depth_val) = obj.get("__DROP_DEPTH__") {
                            if let Some(depth) = depth_val.as_u64() {
                                if depth == 1 {
                                    should_drop_this_array = true;
                                    break;
                                } else if depth > 1 {
                                    return Ok(json!({"__DROP_DEPTH__": depth - 1}));
                                }
                            }
                        }
                    }
                    
                    // Only exclude values that are drop signals, not regular null values
                    if processed_val.as_object().map_or(true, |o| !o.contains_key("__DROP_MARKER__") && !o.contains_key("__DROP_DEPTH__")) {
                        result.push(processed_val);
                    }
                }
                
                if should_drop_this_array {
                    Ok(Value::Null)
                } else {
                    Ok(Value::Array(result))
                }
            },
            _ => {
                // Handle KEEP wrapper - unwrap but don't process further
                if let Some(keep_value) = self.detect_keep_wrapper(&value) {
                    Ok(keep_value)
                } else {
                    Ok(value)
                }
            }
        }
    }
    
    /// Remove empty values while preserving KEEP-wrapped values
    fn remove_empty_values_with_keep(&self, value: Value) -> Value {
        match value {
            Value::Object(map) => {
                let mut result = serde_json::Map::new();
                for (key, val) in map {
                    // Check if this value is marked as KEEP
                    if let Some(obj) = val.as_object() {
                        if let Some(keep_value) = obj.get("__KEEP_MARKER__") {
                            // Always preserve KEEP values regardless of emptiness
                            result.insert(key, keep_value.clone());
                            continue;
                        }
                        if let Some(keep_array) = obj.get("__KEEP_ARRAY_MARKER__") {
                            // Always preserve KEEP arrays regardless of emptiness
                            result.insert(key, keep_array.clone());
                            continue;
                        }
                    }
                    
                    // Check if this value is KEEP-wrapped (fallback)
                    if let Some(keep_value) = self.detect_keep_wrapper(&val) {
                        // Always preserve KEEP values regardless of emptiness
                        result.insert(key, keep_value);
                    } else {
                        let processed = self.remove_empty_values_with_keep(val);
                        
                        // Check if the processed value is a KEEP array marker
                        if let Some(obj) = processed.as_object() {
                            if let Some(keep_array) = obj.get("__KEEP_ARRAY_MARKER__") {
                                result.insert(key, keep_array.clone());
                                continue;
                            }
                        }
                        
                        if self.has_content(&processed) {
                            result.insert(key, processed);
                        }
                    }
                }
                Value::Object(result)
            },
            Value::Array(arr) => {
                let mut result = Vec::new();
                let mut had_keep_markers = false;
                for val in arr {
                    // Check if this value is marked as KEEP
                    if let Some(obj) = val.as_object() {
                        if let Some(keep_value) = obj.get("__KEEP_MARKER__") {
                            // Always preserve KEEP values
                            result.push(keep_value.clone());
                            had_keep_markers = true;
                            continue;
                        }
                    }
                    
                    // Check if this value is KEEP-wrapped (fallback)
                    if let Some(keep_value) = self.detect_keep_wrapper(&val) {
                        // Always preserve KEEP values
                        result.push(keep_value);
                        had_keep_markers = true;
                    } else {
                        let processed = self.remove_empty_values_with_keep(val);
                        if self.has_content(&processed) {
                            result.push(processed);
                        }
                    }
                }
                
                // If this array had KEEP markers, mark it for preservation
                if had_keep_markers {
                    // Mark the array as having KEEP content so it's preserved
                    json!({"__KEEP_ARRAY_MARKER__": result})
                } else {
                    Value::Array(result)
                }
            },
            _ => value,
        }
    }
    
    fn has_content(&self, value: &Value) -> bool {
        crate::has_content(value)
    }
}
