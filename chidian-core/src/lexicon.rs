use pyo3::prelude::*;
use pyo3::types::PyDict;
use pyo3::exceptions::PyKeyError;
use rustc_hash::FxHashMap;

/// High-performance core for bidirectional string mappings
/// Optimized for frequent lookups with minimal FFI overhead
#[pyclass]
pub struct LexiconCore {
    /// Forward mappings: key -> value
    forward: FxHashMap<String, String>,
    /// Reverse mappings: value -> key (for first key in tuple mappings)
    reverse: FxHashMap<String, String>,
    /// Default value for missing keys
    default: Option<String>,
}

#[pymethods]
impl LexiconCore {
    /// Create a new LexiconCore with provided mappings
    #[new]
    fn new(
        forward_mappings: &Bound<'_, PyDict>,
        reverse_mappings: &Bound<'_, PyDict>,
        default: Option<String>,
    ) -> PyResult<Self> {
        let mut forward = FxHashMap::default();
        let mut reverse = FxHashMap::default();

        // Process forward mappings
        for (key, value) in forward_mappings.iter() {
            let key_str: String = key.extract()?;
            let value_str: String = value.extract()?;
            forward.insert(key_str, value_str);
        }

        // Process reverse mappings
        for (key, value) in reverse_mappings.iter() {
            let key_str: String = key.extract()?;
            let value_str: String = value.extract()?;
            reverse.insert(key_str, value_str);
        }

        Ok(LexiconCore {
            forward,
            reverse,
            default,
        })
    }

    /// Bidirectional lookup - checks forward first, then reverse
    /// Returns None if key not found and no default
    fn get_bidirectional(&self, key: &str) -> Option<String> {
        // Try forward lookup first
        if let Some(value) = self.forward.get(key) {
            return Some(value.clone());
        }

        // Try reverse lookup
        if let Some(value) = self.reverse.get(key) {
            return Some(value.clone());
        }

        // Return default if available
        self.default.clone()
    }

    /// Bidirectional lookup that raises KeyError if not found
    fn get_bidirectional_strict(&self, key: &str) -> PyResult<String> {
        match self.get_bidirectional(key) {
            Some(value) => Ok(value),
            None => Err(PyKeyError::new_err(format!("Key '{}' not found", key))),
        }
    }

    /// Check if key exists in either forward or reverse mappings
    fn contains_bidirectional(&self, key: &str) -> bool {
        self.forward.contains_key(key) || self.reverse.contains_key(key)
    }

    /// Forward-only lookup (key -> value)
    fn forward_only(&self, key: &str) -> Option<String> {
        self.forward.get(key).cloned()
    }

    /// Reverse-only lookup (value -> key)
    fn reverse_only(&self, key: &str) -> Option<String> {
        self.reverse.get(key).cloned()
    }

    /// Get all forward mapping keys
    fn forward_keys(&self) -> Vec<String> {
        self.forward.keys().cloned().collect()
    }

    /// Get all reverse mapping keys
    fn reverse_keys(&self) -> Vec<String> {
        self.reverse.keys().cloned().collect()
    }

    /// Get all forward mapping values
    fn forward_values(&self) -> Vec<String> {
        self.forward.values().cloned().collect()
    }

    /// Get all reverse mapping values
    fn reverse_values(&self) -> Vec<String> {
        self.reverse.values().cloned().collect()
    }

    /// Get the number of forward mappings
    fn forward_len(&self) -> usize {
        self.forward.len()
    }

    /// Get the number of reverse mappings
    fn reverse_len(&self) -> usize {
        self.reverse.len()
    }

    /// Get the default value
    fn get_default(&self) -> Option<String> {
        self.default.clone()
    }
}

impl LexiconCore {
    /// Create a new LexiconCore directly from Rust data structures
    /// Used for testing and internal operations
    pub fn from_maps(
        forward: FxHashMap<String, String>,
        reverse: FxHashMap<String, String>,
        default: Option<String>,
    ) -> Self {
        LexiconCore {
            forward,
            reverse,
            default,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rustc_hash::FxHashMap;

    fn create_test_lexicon() -> LexiconCore {
        let mut forward = FxHashMap::default();
        forward.insert("LOINC:123".to_string(), "SNOMED:456".to_string());
        forward.insert("LOINC:789".to_string(), "SNOMED:012".to_string());

        let mut reverse = FxHashMap::default();
        reverse.insert("SNOMED:456".to_string(), "LOINC:123".to_string());
        reverse.insert("SNOMED:012".to_string(), "LOINC:789".to_string());

        LexiconCore::from_maps(forward, reverse, Some("DEFAULT".to_string()))
    }

    #[test]
    fn test_forward_lookup() {
        let lexicon = create_test_lexicon();
        assert_eq!(lexicon.forward_only("LOINC:123"), Some("SNOMED:456".to_string()));
        assert_eq!(lexicon.forward_only("NONEXISTENT"), None);
    }

    #[test]
    fn test_reverse_lookup() {
        let lexicon = create_test_lexicon();
        assert_eq!(lexicon.reverse_only("SNOMED:456"), Some("LOINC:123".to_string()));
        assert_eq!(lexicon.reverse_only("NONEXISTENT"), None);
    }

    #[test]
    fn test_bidirectional_lookup() {
        let lexicon = create_test_lexicon();

        // Forward lookup
        assert_eq!(lexicon.get_bidirectional("LOINC:123"), Some("SNOMED:456".to_string()));

        // Reverse lookup
        assert_eq!(lexicon.get_bidirectional("SNOMED:456"), Some("LOINC:123".to_string()));

        // Default value
        assert_eq!(lexicon.get_bidirectional("NONEXISTENT"), Some("DEFAULT".to_string()));
    }

    #[test]
    fn test_contains_bidirectional() {
        let lexicon = create_test_lexicon();

        // Forward key
        assert!(lexicon.contains_bidirectional("LOINC:123"));

        // Reverse key
        assert!(lexicon.contains_bidirectional("SNOMED:456"));

        // Nonexistent key
        assert!(!lexicon.contains_bidirectional("NONEXISTENT"));
    }

    #[test]
    fn test_collections() {
        let lexicon = create_test_lexicon();

        assert_eq!(lexicon.forward_len(), 2);
        assert_eq!(lexicon.reverse_len(), 2);

        let forward_keys = lexicon.forward_keys();
        assert!(forward_keys.contains(&"LOINC:123".to_string()));
        assert!(forward_keys.contains(&"LOINC:789".to_string()));

        let reverse_keys = lexicon.reverse_keys();
        assert!(reverse_keys.contains(&"SNOMED:456".to_string()));
        assert!(reverse_keys.contains(&"SNOMED:012".to_string()));
    }

    #[test]
    fn test_default_value() {
        let lexicon = create_test_lexicon();
        assert_eq!(lexicon.get_default(), Some("DEFAULT".to_string()));

        let lexicon_no_default = LexiconCore::from_maps(
            FxHashMap::default(),
            FxHashMap::default(),
            None
        );
        assert_eq!(lexicon_no_default.get_default(), None);
        assert_eq!(lexicon_no_default.get_bidirectional("NONEXISTENT"), None);
    }
}
