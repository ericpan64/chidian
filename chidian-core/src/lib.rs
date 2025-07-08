pub mod parser;
pub mod types;
pub mod mutation;

// Re-export main types for easy access
pub use parser::{Path, PathSegment, parse_path};
pub use types::*;
pub use mutation::*;
