use nom::{
    IResult,
    branch::alt,
    character::complete::{char, digit1, one_of},
    combinator::{map, opt, recognize},
    multi::{many0, separated_list0},
    sequence::{delimited, pair, preceded},
};

use crate::selector::PathNode;

// Parse identifiers (used for keys)
fn parse_name(input: &str) -> IResult<&str, &str> {
    recognize(pair(
        one_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"),
        many0(one_of("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"))
    ))(input)
}

// Parse a numeric index
fn parse_number(input: &str) -> IResult<&str, isize> {
    map(
        recognize(pair(opt(char('-')), digit1)),
        |s: &str| s.parse().unwrap()
    )(input)
}

// Parse a single index [n]
fn parse_single_index(input: &str) -> IResult<&str, PathNode> {
    map(
        delimited(char('['), parse_number, char(']')),
        PathNode::Index
    )(input)
}

// Parse a wildcard [*]
fn parse_wildcard(input: &str) -> IResult<&str, PathNode> {
    map(
        delimited(char('['), char('*'), char(']')),
        |_| PathNode::Wildcard
    )(input)
}

// Parse a slice [start:end]
fn parse_slice(input: &str) -> IResult<&str, PathNode> {
    map(
        delimited(
            char('['),
            pair(opt(parse_number), preceded(char(':'), opt(parse_number))),
            char(']')
        ),
        |(start, end)| PathNode::Slice(start, end)
    )(input)
}

// Parse any bracket-based accessor: [n], [*], or [start:end]
fn parse_bracket_accessor(input: &str) -> IResult<&str, PathNode> {
    alt((parse_single_index, parse_wildcard, parse_slice))(input)
}

// Parse a dot-notation key access (.property)
fn parse_key_access(input: &str) -> IResult<&str, PathNode> {
    map(
        preceded(char('.'), parse_name),
        |s| PathNode::Key(s.to_string())
    )(input)
}

// Parse a bare identifier without a dot prefix
fn parse_bare_key(input: &str) -> IResult<&str, PathNode> {
    map(
        parse_name,
        |s| PathNode::Key(s.to_string())
    )(input)
}

// Parse a group element (can be a key access or bracket accessor)
fn parse_group_element(input: &str) -> IResult<&str, PathNode> {
    alt((parse_key_access, parse_bracket_accessor))(input)
}

// Parse a group of items (a, b, c)
fn parse_group(input: &str) -> IResult<&str, PathNode> {
    map(
        delimited(
            char('('),
            separated_list0(
                char(','),
                parse_group_element
            ),
            char(')')
        ),
        PathNode::Group
    )(input)
}

// Parse a single path element (either key.subkey or [index] or group)
fn parse_path_element(input: &str) -> IResult<&str, PathNode> {
    alt((parse_bracket_accessor, parse_key_access, parse_group))(input)
}

// Parse a sequence of path elements
fn parse_path_elements(input: &str) -> IResult<&str, Vec<PathNode>> {
    many0(parse_path_element)(input)
}

// Parse a selector expression with an leading key
fn parse_full_selector(input: &str) -> IResult<&str, Vec<PathNode>> {
    // Handle the special case of a selector starting with a bracket
    if input.starts_with('[') {
        let (remaining, bracket_node) = parse_bracket_accessor(input)?;
        let (remaining, rest) = parse_path_elements(remaining)?;
        
        let mut nodes = vec![bracket_node];
        nodes.extend(rest);
        
        return Ok((remaining, nodes));
    }
    
    // Normal case: starts with a key
    let (remaining, first_part) = parse_bare_key(input)?;
    let (remaining, rest) = parse_path_elements(remaining)?;
    
    let mut nodes = vec![first_part];
    nodes.extend(rest);
    
    Ok((remaining, nodes))
}

/// Parse a selector string into a vector of PathNode elements
pub fn parse_selector(input: &str) -> Result<Vec<PathNode>, String> {
    // Preprocess: trim whitespace
    let input = input.trim();
    
    // Check if input is empty
    if input.is_empty() {
        return Ok(Vec::new());
    }
    
    // Check if input starts with a dot and return a specific error
    if input.starts_with('.') {
        return Err(format!("Selector cannot start with a dot. Use '{}' instead.", &input[1..]));
    }
    
    match parse_full_selector(input) {
        Ok((rest, nodes)) if rest.is_empty() => Ok(nodes),
        Ok((rest, _)) => Err(format!("Incomplete parsing: '{}' remains", rest)),
        Err(e) => Err(format!("Parse error: {}", e)),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_key() {
        assert!(matches!(
            parse_key_access(".user"),
            Ok((_, PathNode::Key(key))) if key == "user"
        ));
    }

    #[test]
    fn test_bare_key() {
        assert!(matches!(
            parse_bare_key("user"),
            Ok((_, PathNode::Key(key))) if key == "user"
        ));
    }

    #[test]
    fn test_parse_index() {
        assert!(matches!(
            parse_single_index("[0]"),
            Ok((_, PathNode::Index(idx))) if idx == 0
        ));

        assert!(matches!(
            parse_single_index("[-1]"),
            Ok((_, PathNode::Index(idx))) if idx == -1
        ));
    }

    #[test]
    fn test_parse_wildcard() {
        assert!(matches!(
            parse_wildcard("[*]"),
            Ok((_, PathNode::Wildcard))
        ));
    }

    #[test]
    fn test_parse_slice() {
        let (_, node) = parse_slice("[1:3]").unwrap();
        if let PathNode::Slice(start, end) = node {
            assert_eq!(start, Some(1));
            assert_eq!(end, Some(3));
        } else {
            panic!("Expected Slice node");
        }

        let (_, node) = parse_slice("[:3]").unwrap();
        if let PathNode::Slice(start, end) = node {
            assert_eq!(start, None);
            assert_eq!(end, Some(3));
        } else {
            panic!("Expected Slice node");
        }

        let (_, node) = parse_slice("[1:]").unwrap();
        if let PathNode::Slice(start, end) = node {
            assert_eq!(start, Some(1));
            assert_eq!(end, None);
        } else {
            panic!("Expected Slice node");
        }
    }

    #[test]
    fn test_parse_path() {
        let path = parse_selector("users[0].name").unwrap();
        assert_eq!(path.len(), 3);
        assert!(matches!(path[0], PathNode::Key(ref k) if k == "users"));
        assert!(matches!(path[1], PathNode::Index(0)));
        assert!(matches!(path[2], PathNode::Key(ref k) if k == "name"));
    }

    #[test]
    fn test_parse_path_without_leading_dot() {
        let path = parse_selector("users[0].name").unwrap();
        assert_eq!(path.len(), 3);
        assert!(matches!(path[0], PathNode::Key(ref k) if k == "users"));
        assert!(matches!(path[1], PathNode::Index(0)));
        assert!(matches!(path[2], PathNode::Key(ref k) if k == "name"));
    }

    #[test]
    fn test_parse_bracket_only() {
        let path = parse_selector("[0]").unwrap();
        assert_eq!(path.len(), 1);
        assert!(matches!(path[0], PathNode::Index(0)));
    }

    #[test]
    fn test_parse_empty() {
        let path = parse_selector("").unwrap();
        assert_eq!(path.len(), 0);
    }

    #[test]
    fn test_parse_group() {
        let (_, node) = parse_group("(.first,.second)").unwrap();
        if let PathNode::Group(elements) = node {
            assert_eq!(elements.len(), 2);
            assert!(matches!(elements[0], PathNode::Key(ref k) if k == "first"));
            assert!(matches!(elements[1], PathNode::Key(ref k) if k == "second"));
        } else {
            panic!("Expected Group node");
        }
    }

    #[test]
    fn test_parse_complex_path_with_group() {
        let path = parse_selector("users(.name,.age)").unwrap();
        assert_eq!(path.len(), 2);
        assert!(matches!(path[0], PathNode::Key(ref k) if k == "users"));
        if let PathNode::Group(elements) = &path[1] {
            assert_eq!(elements.len(), 2);
            assert!(matches!(elements[0], PathNode::Key(ref k) if k == "name"));
            assert!(matches!(elements[1], PathNode::Key(ref k) if k == "age"));
        } else {
            panic!("Expected Group node");
        }
    }
} 