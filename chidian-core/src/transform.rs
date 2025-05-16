use serde_json::Value;

/// A trait for applying transformations to JSON values.
/// Transformations are chainable and immutable - they don't modify the input value.
pub trait Transform: Send + Sync {
    /// Apply a transformation to a JSON value and return the transformed value.
    fn apply(&self, value: Value) -> Value;
    
    /// Clone this transformer into a new boxed instance.
    fn box_clone(&self) -> Box<dyn Transform>;
}

impl Clone for Box<dyn Transform> {
    fn clone(&self) -> Self {
        self.box_clone()
    }
}

/// Chain multiple transformations together, applying them in sequence.
pub fn chain_transforms(value: Value, transforms: &[Box<dyn Transform>]) -> Value {
    transforms.iter().fold(value, |acc, transform| transform.apply(acc))
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;
    
    // A simple transformation that doubles numeric values
    #[derive(Clone)]
    struct DoubleNumbers;
    
    impl Transform for DoubleNumbers {
        fn apply(&self, value: Value) -> Value {
            match value {
                Value::Number(n) => {
                    if let Some(i) = n.as_i64() {
                        json!(i * 2)
                    } else if let Some(f) = n.as_f64() {
                        json!(f * 2.0)
                    } else {
                        Value::Number(n)
                    }
                },
                Value::Array(items) => {
                    let transformed: Vec<Value> = items.into_iter()
                        .map(|item| self.apply(item))
                        .collect();
                    Value::Array(transformed)
                },
                Value::Object(map) => {
                    let mut transformed = serde_json::Map::new();
                    for (k, v) in map {
                        transformed.insert(k, self.apply(v));
                    }
                    Value::Object(transformed)
                },
                _ => value,
            }
        }
        
        fn box_clone(&self) -> Box<dyn Transform> {
            Box::new(self.clone())
        }
    }
    
    #[test]
    fn test_apply_transform() {
        let value = json!({"numbers": [1, 2, 3]});
        let transform = DoubleNumbers;
        
        let result = transform.apply(value);
        assert_eq!(result, json!({"numbers": [2, 4, 6]}));
    }
    
    #[test]
    fn test_chain_transforms() {
        let value = json!(5);
        let transforms: Vec<Box<dyn Transform>> = vec![
            Box::new(DoubleNumbers),
            Box::new(DoubleNumbers), // Apply twice
        ];
        
        let result = chain_transforms(value, &transforms);
        assert_eq!(result, json!(20)); // 5 -> 10 -> 20
    }
} 