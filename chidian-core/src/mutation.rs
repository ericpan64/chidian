use crate::parser::{Path, PathSegment};
use crate::types::{TraversalError, TraversalResult};

/// Container type determination for path mutation
#[derive(Debug, Clone, PartialEq)]
pub enum ContainerType {
    Dict,
    List,
}

/// Determine what type of container is needed for the next segment
pub fn determine_container_type(
    segments: &[PathSegment],
    current_index: usize,
) -> ContainerType {
    if current_index + 1 < segments.len() {
        // Look at the next segment to determine container type
        match &segments[current_index + 1] {
            PathSegment::Index(_) => ContainerType::List,
            PathSegment::Key(_) => ContainerType::Dict,
            PathSegment::Slice(_, _) => ContainerType::List,
            PathSegment::Wildcard => ContainerType::List,
            PathSegment::Tuple(_) => ContainerType::List,
        }
    } else {
        // This is the penultimate segment - look at the final segment
        if let Some(final_segment) = segments.last() {
            match final_segment {
                PathSegment::Index(_) => ContainerType::List,
                _ => ContainerType::Dict,
            }
        } else {
            ContainerType::Dict
        }
    }
}

/// Expand a list to accommodate the given index
pub fn expand_list_for_index(
    list_len: usize,
    target_index: i32,
    strict: bool,
) -> TraversalResult<Option<usize>> {
    if target_index >= 0 {
        // Positive index - we can expand
        Ok(Some(target_index as usize))
    } else {
        // Negative indexing - only works on existing items
        let actual_idx = list_len as i32 + target_index;
        if actual_idx < 0 {
            if strict {
                Err(TraversalError::IndexOutOfRange(target_index))
            } else {
                Ok(None) // Signal error in non-strict mode
            }
        } else {
            Ok(Some(actual_idx as usize))
        }
    }
}

/// Validate that a path is suitable for mutation operations
pub fn validate_mutation_path(path: &Path) -> TraversalResult<()> {
    if path.segments.is_empty() {
        return Err(TraversalError::InvalidPath("Empty path".to_string()));
    }

    // Check if path starts with index - we don't support arrays at root
    if let Some(PathSegment::Index(_)) = path.segments.first() {
        return Err(TraversalError::InvalidPath(
            "Cannot create array at root level - path must start with a key".to_string(),
        ));
    }

    // Validate segments for mutation compatibility
    for (i, segment) in path.segments.iter().enumerate() {
        match segment {
            PathSegment::Wildcard => {
                return Err(TraversalError::InvalidPath(
                    format!("Wildcard not supported in mutation path at position {}", i),
                ));
            }
            PathSegment::Slice(_, _) => {
                return Err(TraversalError::InvalidPath(
                    format!("Slice not supported in mutation path at position {}", i),
                ));
            }
            PathSegment::Tuple(_) => {
                return Err(TraversalError::InvalidPath(
                    format!("Tuple not supported in mutation path at position {}", i),
                ));
            }
            _ => {} // Key and Index are valid
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parser::parse_path;

    #[test]
    fn test_determine_container_type() {
        let (_, path) = parse_path("patient.name").unwrap();
        assert_eq!(
            determine_container_type(&path.segments, 0),
            ContainerType::Dict
        );

        let (_, path) = parse_path("items[0].value").unwrap();
        assert_eq!(
            determine_container_type(&path.segments, 0),
            ContainerType::List
        );
    }

    #[test]
    fn test_expand_list_for_index() {
        // Positive index
        assert_eq!(expand_list_for_index(3, 5, false).unwrap(), Some(5));

        // Negative index within bounds
        assert_eq!(expand_list_for_index(5, -2, false).unwrap(), Some(3));

        // Negative index out of bounds, non-strict
        assert_eq!(expand_list_for_index(2, -5, false).unwrap(), None);

        // Negative index out of bounds, strict
        assert!(expand_list_for_index(2, -5, true).is_err());
    }

    #[test]
    fn test_validate_mutation_path() {
        let (_, valid_path) = parse_path("patient.name").unwrap();
        assert!(validate_mutation_path(&valid_path).is_ok());

        let (_, invalid_path) = parse_path("[0].name").unwrap();
        assert!(validate_mutation_path(&invalid_path).is_err());

        let (_, wildcard_path) = parse_path("items[*].name").unwrap();
        assert!(validate_mutation_path(&wildcard_path).is_err());
    }
}
