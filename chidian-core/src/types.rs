use std::fmt;

/// Error type for traversal operations
#[derive(Debug, Clone)]
pub enum TraversalError {
    KeyNotFound(String),
    IndexOutOfRange(i32),
    TypeMismatch(String),
    InvalidPath(String),
    Custom(String),
}

impl fmt::Display for TraversalError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            TraversalError::KeyNotFound(key) => write!(f, "Key '{}' not found", key),
            TraversalError::IndexOutOfRange(idx) => write!(f, "Index {} out of range", idx),
            TraversalError::TypeMismatch(msg) => write!(f, "Type mismatch: {}", msg),
            TraversalError::InvalidPath(path) => write!(f, "Invalid path: {}", path),
            TraversalError::Custom(msg) => write!(f, "{}", msg),
        }
    }
}

impl std::error::Error for TraversalError {}

/// Result type for traversal operations
pub type TraversalResult<T> = Result<T, TraversalError>;