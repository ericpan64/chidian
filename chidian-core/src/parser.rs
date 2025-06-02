use nom::{
    IResult,
    branch::alt,
    bytes::complete::{tag, take_while1},
    character::complete::{char, digit1},
    combinator::{map, opt, recognize},
    multi::separated_list1,
    sequence::{delimited, tuple},
};
use std::str::FromStr;

#[derive(Debug, Clone, PartialEq)]
pub enum PathSegment {
    Key(String),
    Index(i32),
    Slice(Option<i32>, Option<i32>),
    Wildcard,
    Tuple(Vec<Path>),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Path {
    pub segments: Vec<PathSegment>,
}

// Parser for valid identifier characters
fn is_identifier_char(c: char) -> bool {
    c.is_alphanumeric() || c == '_' || c == '-'
}

// Parse a key name (alphanumeric + underscore + hyphen)
fn parse_key(input: &str) -> IResult<&str, PathSegment> {
    map(take_while1(is_identifier_char), |s: &str| {
        PathSegment::Key(s.to_string())
    })(input)
}

// Parse a signed integer
fn parse_integer(input: &str) -> IResult<&str, i32> {
    map(recognize(tuple((opt(char('-')), digit1))), |s: &str| {
        i32::from_str(s).unwrap()
    })(input)
}

// Parse array index like [0] or [-1]
fn parse_index(input: &str) -> IResult<&str, PathSegment> {
    map(
        delimited(char('['), parse_integer, char(']')),
        PathSegment::Index,
    )(input)
}

// Parse wildcard [*]
fn parse_wildcard(input: &str) -> IResult<&str, PathSegment> {
    map(tag("[*]"), |_| PathSegment::Wildcard)(input)
}

// Parse slice like [1:3] or [:3] or [1:]
fn parse_slice(input: &str) -> IResult<&str, PathSegment> {
    delimited(
        char('['),
        map(
            tuple((opt(parse_integer), char(':'), opt(parse_integer))),
            |(start, _, end)| PathSegment::Slice(start, end),
        ),
        char(']'),
    )(input)
}

// Parse whitespace
fn ws(input: &str) -> IResult<&str, &str> {
    use nom::error::Error;
    take_while1::<_, _, Error<&str>>(|c: char| c.is_whitespace())(input).or(Ok((input, "")))
}

// Parse key followed by optional brackets
fn parse_key_with_brackets(input: &str) -> IResult<&str, Vec<PathSegment>> {
    let (input, key) = parse_key(input)?;
    let mut segments = vec![key];

    // Parse any following brackets
    let mut remaining = input;
    loop {
        if let Ok((new_remaining, bracket)) =
            alt((parse_wildcard, parse_slice, parse_index))(remaining)
        {
            segments.push(bracket);
            remaining = new_remaining;
        } else {
            break;
        }
    }

    Ok((remaining, segments))
}

// Parse a complete path (handles paths starting with brackets)
pub fn parse_path(input: &str) -> IResult<&str, Path> {
    // Check if path starts with a bracket
    if input.starts_with('[') {
        let (remaining, first_segments) = parse_path_segment_or_key_with_brackets(input)?;

        if remaining.is_empty() {
            return Ok((
                remaining,
                Path {
                    segments: first_segments,
                },
            ));
        }

        // If there's more path after the initial bracket
        if remaining.starts_with('.') {
            let (remaining, _) = char('.')(remaining)?;
            let (remaining, rest) =
                separated_list1(char('.'), parse_path_segment_or_key_with_brackets)(remaining)?;

            let mut all_segments = first_segments;
            for segment_group in rest {
                all_segments.extend(segment_group);
            }

            return Ok((
                remaining,
                Path {
                    segments: all_segments,
                },
            ));
        }

        Ok((
            remaining,
            Path {
                segments: first_segments,
            },
        ))
    } else {
        // Normal path parsing
        map(
            separated_list1(char('.'), parse_path_segment_or_key_with_brackets),
            |segment_groups| Path {
                segments: segment_groups.into_iter().flatten().collect(),
            },
        )(input)
    }
}

// Parse a single path (for use in tuples)
fn parse_single_path(input: &str) -> IResult<&str, Path> {
    parse_path(input)
}

// Parse tuple like (id,name) or (id,inner.msg) with optional whitespace
fn parse_tuple(input: &str) -> IResult<&str, PathSegment> {
    map(
        delimited(
            tuple((char('('), ws)),
            separated_list1(
                tuple((ws, char(','), ws)),
                delimited(ws, parse_single_path, ws),
            ),
            tuple((ws, char(')'))),
        ),
        PathSegment::Tuple,
    )(input)
}

// Parse any path segment or key with brackets
fn parse_path_segment_or_key_with_brackets(input: &str) -> IResult<&str, Vec<PathSegment>> {
    alt((
        map(parse_wildcard, |seg| vec![seg]),
        map(parse_slice, |seg| vec![seg]),
        map(parse_index, |seg| vec![seg]),
        map(parse_tuple, |seg| vec![seg]),
        parse_key_with_brackets,
    ))(input)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_simple_path() {
        let (_, path) = parse_path("patient.name").unwrap();
        assert_eq!(path.segments.len(), 2);
        assert_eq!(path.segments[0], PathSegment::Key("patient".to_string()));
        assert_eq!(path.segments[1], PathSegment::Key("name".to_string()));
    }

    #[test]
    fn test_parse_path_with_index() {
        let (_, path) = parse_path("items[0].name").unwrap();
        assert_eq!(path.segments.len(), 3);
        assert_eq!(path.segments[0], PathSegment::Key("items".to_string()));
        assert_eq!(path.segments[1], PathSegment::Index(0));
        assert_eq!(path.segments[2], PathSegment::Key("name".to_string()));
    }

    #[test]
    fn test_parse_wildcard() {
        let (_, path) = parse_path("items[*].id").unwrap();
        assert_eq!(path.segments.len(), 3);
        assert_eq!(path.segments[0], PathSegment::Key("items".to_string()));
        assert_eq!(path.segments[1], PathSegment::Wildcard);
        assert_eq!(path.segments[2], PathSegment::Key("id".to_string()));
    }
}
