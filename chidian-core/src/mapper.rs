use serde_json::Value;
use std::error::Error;
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

use crate::{Chainable, DROP, KEEP, JsonContainer};

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

    pub fn with_config(&mut self, config: MapperConfig) -> () {
        self.config = config;
    }

    pub fn map(&self, data: Value) -> Result<Value, Box<dyn Error>> {
        // TODO: Handle the different config options (remove_empty, strict, use_nesting_cache)
        // Create a new MappingContext
        let context = MappingContext::new(data);
        // Run the mapping function
        let result_context = self.mapping_fn.run(context)?;
        // TODO: Clean-up + handle the enums accordingly (DROP, KEEP)
        Ok(result_context.data)
    }
}

// // Custom serialization/deserialization methods for Mapper
// impl<'a> Mapper<'a> {
//     // TODO: Make this work correctly. Also figure out semantics for `mapping_fn` (e.g. best way to serialize/deserialize a function?)
//     pub fn to_json(&self) -> Result<Value, Box<dyn Error>> {
//         // Create a serializable representation
//         let mut map = serde_json::Map::new();
        
//         // We can't serialize the function reference directly
//         // This would need custom handling based on your requirements
//         map.insert("mapping_fn".to_string(), Value::String("function_reference".to_string()));
        
//         // Serialize the config
//         map.insert("config".to_string(), serde_json::to_value(&self.config)?);
        
//         Ok(Value::Object(map))
//     }

//     // TODO: Same as above
//     pub fn from_json(json: Value) -> Result<Self, Box<dyn Error>> {
//         // Custom deserialization needed since we can't automatically deserialize the function
//         let config = serde_json::from_value::<MapperConfig>(
//             json.get("config").cloned().unwrap_or(Value::Null)
//         )?;
        
//         // This is a placeholder - we still need to figure out how to handle mapping_fn
//         let mapping_fn_str = json.get("mapping_fn").and_then(|v| v.as_str()).unwrap_or_default();
        
//         // This part would need custom handling based on how you're storing the function
//         // For now, this is just a placeholder that won't compile
//         Err("Deserialization of Mapper is not fully implemented yet".into())
//     }

//     // TODO: Pseudocode for mapper.rs to handle DROP enum, verify logic
//     /// Process a DROP instruction during mapping
//     /// 
//     /// This function should be called when a DROP enum value is encountered
//     /// during the mapping process. It determines which container in the
//     /// ancestry chain should be deleted based on the DROP variant.
//     ///
//     /// Parameters:
//     /// - drop_type: The DROP enum value indicating which relative object to remove
//     /// - ancestry: A stack or list representing the path from root to current value
//     ///             Each entry contains the container and the key/index used to access its child
//     ///
//     /// Returns:
//     /// - MappingContext with modified structure where the specified container is removed
//     fn handle_drop(drop_type: DROP, ancestry: &[ContainerContext]) -> Result<MappingContext, Box<dyn Error>> {
//         // Determine depth based on DROP variant
//         let depth = match drop_type {
//             DROP::ThisObject => 0,
//             DROP::Parent => 1,
//             DROP::Grandparent => 2,
//             DROP::GreatGrandparent => 3,
//         };
        
//         // Check if we have enough ancestry depth
//         if ancestry.len() <= depth {
//             return Err("Cannot DROP: Not enough container depth in ancestry".into());
//         }
        
//         // Get the container to be removed and its parent
//         let target_index = ancestry.len() - 1 - depth;
        
//         // If we're dropping the root object
//         if target_index == 0 {
//             // Create empty result
//             return Ok(MappingContext::new_empty());
//         }
        
//         // Get the parent of the container to be dropped
//         let parent_index = target_index - 1;
//         let parent = &ancestry[parent_index];
        
//         // Get access information (key or index) for the target in its parent
//         let access_info = &ancestry[target_index].access_info;
        
//         // Remove the target from its parent
//         let mut modified_context = MappingContext::clone_from_ancestry(ancestry, parent_index);
        
//         match parent.container {
//             JsonContainer::Object(ref mut map) => {
//                 if let AccessInfo::Key(key) = access_info {
//                     map.remove(key);
//                 } else {
//                     return Err("Invalid access info for object container".into());
//                 }
//             },
//             JsonContainer::Array(ref mut vec) => {
//                 if let AccessInfo::Index(idx) = access_info {
//                     if *idx < vec.len() {
//                         vec.remove(*idx);
//                     } else {
//                         return Err("Array index out of bounds".into());
//                     }
//                 } else {
//                     return Err("Invalid access info for array container".into());
//                 }
//             }
//         }
        
//         Ok(modified_context)
//     }

//     // Pseudocode for mapper.rs to handle KEEP struct:

//     /// Process a value that might be wrapped in KEEP during mapping
//     /// 
//     /// This function should be called when processing values that might be
//     /// wrapped in KEEP, especially during the remove_empty_values operation.
//     ///
//     /// Parameters:
//     /// - value: The JSON value to check for KEEP wrapping
//     /// - is_removing_empty: Whether we're currently in a remove_empty operation
//     ///
//     /// Returns:
//     /// - The unwrapped value if it's a KEEP, otherwise the original value
//     /// - A boolean indicating if this value should be preserved regardless of emptiness
//     fn process_keep_value(value: &Value, is_removing_empty: bool) -> (Value, bool) {
//         // Try to deserialize as KEEP
//         if let Ok(keep) = serde_json::from_value::<KEEP>(value.clone()) {
//             // If we're removing empty values, indicate this should be preserved
//             if is_removing_empty {
//                 return (keep.value, true);
//             } else {
//                 // Just unwrap the value
//                 return (keep.value, false);
//             }
//         }
        
//         // Not a KEEP value
//         (value.clone(), false)
//     }

//     /// Enhanced version of remove_empty_values for use in the mapper
//     /// 
//     /// This integrates with the mapping context to properly handle KEEP values
//     /// during the empty value removal process.
//     ///
//     /// Parameters:
//     /// - context: The current mapping context containing the value to process
//     ///
//     /// Returns:
//     /// - Updated mapping context with empty values removed, but KEEP values preserved
//     fn mapper_remove_empty_values(context: MappingContext) -> Result<MappingContext, Box<dyn Error>> {
//         let value = context.value();
        
//         // Process the value, checking for KEEP wrapping at each level
//         let process_value = |v: Value| -> Value {
//             // If this is a KEEP-wrapped value, preserve it regardless of emptiness
//             if let Ok(keep) = serde_json::from_value::<KEEP>(v.clone()) {
//                 return keep.value;
//             }
            
//             match v {
//                 Value::Object(map) => {
//                     let mut result = serde_json::Map::new();
//                     for (k, item) in map {
//                         // Process each child value
//                         let processed = process_value(item);
//                         let (unwrapped, preserve) = process_keep_value(&processed, true);
                        
//                         // Keep the value if it has content or is explicitly marked for preservation
//                         if preserve || has_content(&unwrapped) {
//                             result.insert(k, unwrapped);
//                         }
//                     }
//                     Value::Object(result)
//                 },
//                 Value::Array(arr) => {
//                     let mut result = Vec::new();
//                     for item in arr {
//                         // Process each array item
//                         let processed = process_value(item);
//                         let (unwrapped, preserve) = process_keep_value(&processed, true);
                        
//                         // Keep the value if it has content or is explicitly marked for preservation
//                         if preserve || has_content(&unwrapped) {
//                             result.push(unwrapped);
//                         }
//                     }
//                     Value::Array(result)
//                 },
//                 // Other primitive values remain unchanged
//                 _ => v,
//             }
//         };
        
//         // Process the root value
//         let processed = process_value(value);
        
//         // Create a new mapping context with the processed value
//         Ok(MappingContext::new(processed))
//     }
// }