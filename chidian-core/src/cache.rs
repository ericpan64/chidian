use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use once_cell::sync::Lazy;

use crate::selector::{Selector, Result as SelectorResult};

// Global selector cache using a Lazy-initialized Mutex-protected HashMap
static SELECTOR_CACHE: Lazy<Mutex<HashMap<String, Arc<Selector>>>> = Lazy::new(|| {
    Mutex::new(HashMap::new())
});

/// Get a selector from the cache or parse and cache it
pub fn get_cached_selector(selector_str: &str) -> SelectorResult<Arc<Selector>> {
    // Check if the selector is already in the cache
    let cache_result = {
        let cache = SELECTOR_CACHE.lock().map_err(|_| 
            crate::selector::SelectorError::ParseError("Cache lock poisoned".to_string())
        )?;
        cache.get(selector_str).cloned()
    };
    
    // If cached, return it
    if let Some(selector) = cache_result {
        return Ok(selector);
    }
    
    // Not cached, parse and cache it
    let selector = Selector::parse(selector_str)?;
    
    // Insert into cache
    {
        let mut cache = SELECTOR_CACHE.lock().map_err(|_| 
            crate::selector::SelectorError::ParseError("Cache lock poisoned".to_string())
        )?;
        cache.insert(selector_str.to_string(), Arc::clone(&selector));
    }
    
    Ok(selector)
}

/// Clear the selector cache
pub fn clear_cache() -> SelectorResult<()> {
    let mut cache = SELECTOR_CACHE.lock().map_err(|_| 
        crate::selector::SelectorError::ParseError("Cache lock poisoned".to_string())
    )?;
    cache.clear();
    Ok(())
}

/// Get the number of items in the cache
pub fn cache_size() -> SelectorResult<usize> {
    let cache = SELECTOR_CACHE.lock().map_err(|_| 
        crate::selector::SelectorError::ParseError("Cache lock poisoned".to_string())
    )?;
    Ok(cache.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    
    #[test]
    fn test_cache_functionality() -> SelectorResult<()> {
        // Start with a clean cache
        {
            let mut cache = SELECTOR_CACHE.lock().map_err(|_| 
                crate::selector::SelectorError::ParseError("Cache lock poisoned".to_string())
            )?;
            cache.clear();
        }
        
        // First parse 
        let selector1 = get_cached_selector(".user.name")?;
        
        // Second parse of same string - should retrieve from cache
        let selector2 = get_cached_selector(".user.name")?;
        
        // Arc pointers should point to same data
        assert!(Arc::ptr_eq(&selector1, &selector2), 
               "Cached selectors should point to the same memory");
        
        // Verify the selector works
        let data = json!({"user": {"name": "John"}});
        let result = selector1.evaluate(&data)?;
        assert_eq!(result, json!("John"));
        
        Ok(())
    }
} 