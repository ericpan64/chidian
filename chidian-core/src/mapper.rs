use serde_json::Value;
use std::error::Error;
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

use crate::Chainable;

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
    pub remove_empty: bool,
    pub strict: bool,
    pub use_cache: bool,
    pub implementation_notes: HashMap<String, String>
}

impl MapperConfig {
    pub fn new(remove_empty: bool, strict: bool, use_cache: bool, implementation_notes: HashMap<String, String>) -> Self {
        return MapperConfig {
            remove_empty,
            strict,
            use_cache,
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
        // Create a new MappingContext
        let context = MappingContext::new(data);
        let result_context = self.mapping_fn.run(context)?;
        Ok(result_context.data)
    }
}

// Custom serialization/deserialization methods for Mapper
impl<'a> Mapper<'a> {
    // TODO: Make this work correctly. Also figure out semantics for `mapping_fn` (e.g. best way to serialize/deserialize a function?)
    pub fn to_json(&self) -> Result<Value, Box<dyn Error>> {
        // Create a serializable representation
        let mut map = serde_json::Map::new();
        
        // We can't serialize the function reference directly
        // This would need custom handling based on your requirements
        map.insert("mapping_fn".to_string(), Value::String("function_reference".to_string()));
        
        // Serialize the config
        map.insert("config".to_string(), serde_json::to_value(&self.config)?);
        
        Ok(Value::Object(map))
    }

    // TODO: Same as above
    pub fn from_json(json: Value) -> Result<Self, Box<dyn Error>> {
        // Custom deserialization needed since we can't automatically deserialize the function
        let config = serde_json::from_value::<MapperConfig>(
            json.get("config").cloned().unwrap_or(Value::Null)
        )?;
        
        // This is a placeholder - we still need to figure out how to handle mapping_fn
        let mapping_fn_str = json.get("mapping_fn").and_then(|v| v.as_str()).unwrap_or_default();
        
        // This part would need custom handling based on how you're storing the function
        // For now, this is just a placeholder that won't compile
        Err("Deserialization of Mapper is not fully implemented yet".into())
    }
}