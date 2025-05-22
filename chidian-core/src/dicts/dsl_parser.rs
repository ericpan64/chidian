/// Nom parser for DSL
///
/// Rough PEG grammar (for reference -- trust the actual code for behavior):
/// ```peg
/// # === Get DSL ===
/// #  NOTE: Assume whitespace is removed beforehand
/// get_expr = key (dot key)*
/// key = (list_op / single / tuple)
/// 
/// # === Actionable Units ===
/// single = name single_index?
/// list_op = name? multi_index
/// tuple = lparen nested_expr (comma nested_expr)* rparen
/// 
/// # === Intermediate Representation ===
/// single_index = lbrack number rbrack
/// multi_index = lbrack (star / slice) rbrack
/// slice = number? colon number?
/// nested_expr = key (dot key)*  # Re-defining so can handle separately
/// 
/// # === Primitives ===
/// lbrack = "["
/// rbrack = "]"
/// lparen = "("
/// rparen = ")"
/// comma = ","
/// colon = ":"
/// dot = "."
/// star = "*"
/// 
/// # === Lexemes ===
/// name = ~"[a-zA-Z_][a-zA-Z0-9_]*"
/// number = ~"-?[0-9]+"
/// ```

use nom::{
    IResult,
    branch::alt,
    bytes::complete::{tag, take_while1, take_while},
    character::complete::{char, digit1, space0, alpha1, alphanumeric1},
    combinator::{map, opt, recognize, verify},
    multi::{many0, separated_list0},
    sequence::{delimited, pair, preceded, terminated, tuple},
};

#[derive(Debug, Clone, PartialEq)]
pub enum IndexOp {
    Single(i32),
    Slice(Option<i32>, Option<i32>),
    Star,
}

#[derive(Debug, Clone, PartialEq)]
pub enum GetActionableUnit {
    Single { name: String, index: Option<IndexOp> },
    ListOp { name: Option<String>, index: IndexOp },
    Tuple(Vec<GetExpr>),
}

#[derive(Debug, Clone, PartialEq)]
pub struct GetExpr {
    pub units: Vec<GetActionableUnit>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ParsedGetExpr {
    pub expr: GetExpr,
}

// Parse identifier (name)
fn identifier(input: &str) -> IResult<&str, String> {
    map(
        recognize(pair(
            alt((alpha1, tag("_"))),
            take_while(|c: char| c.is_ascii_alphanumeric() || c == '_'),
        )),
        |s: &str| s.to_string(),
    )(input)
}

// Parse number (including negative)
fn number(input: &str) -> IResult<&str, i32> {
    map(
        recognize(pair(opt(char('-')), digit1)),
        |s: &str| s.parse().unwrap(),
    )(input)
}

// Parse single index [42] or [-1]
fn single_index(input: &str) -> IResult<&str, IndexOp> {
    map(
        delimited(char('['), number, char(']')),
        IndexOp::Single,
    )(input)
}

// Parse slice [start:end], [:end], [start:], or [:]
fn slice_index(input: &str) -> IResult<&str, IndexOp> {
    map(
        delimited(
            char('['),
            tuple((opt(number), char(':'), opt(number))),
            char(']'),
        ),
        |(start, _, end)| IndexOp::Slice(start, end),
    )(input)
}

// Parse star [*]
fn star_index(input: &str) -> IResult<&str, IndexOp> {
    map(
        delimited(char('['), char('*'), char(']')),
        |_| IndexOp::Star,
    )(input)
}

// Parse any index operation
fn index_op(input: &str) -> IResult<&str, IndexOp> {
    alt((star_index, slice_index, single_index))(input)
}

// Parse a single unit (name with optional single index)
fn single_unit(input: &str) -> IResult<&str, GetActionableUnit> {
    map(
        pair(identifier, opt(single_index)),
        |(name, index)| GetActionableUnit::Single { 
            name, 
            index: index.map(|idx| match idx {
                IndexOp::Single(n) => IndexOp::Single(n),
                _ => unreachable!(),
            })
        },
    )(input)
}

// Parse a list operation (optional name with multi-index)
fn list_op_unit(input: &str) -> IResult<&str, GetActionableUnit> {
    map(
        pair(opt(identifier), alt((star_index, slice_index))),
        |(name, index)| GetActionableUnit::ListOp { name, index },
    )(input)
}

// Forward declaration for recursive parsing
fn get_expr(input: &str) -> IResult<&str, GetExpr>;

// Parse tuple (parentheses with comma-separated expressions)
fn tuple_unit(input: &str) -> IResult<&str, GetActionableUnit> {
    map(
        delimited(
            char('('),
            separated_list0(
                delimited(space0, char(','), space0),
                get_expr,
            ),
            char(')'),
        ),
        GetActionableUnit::Tuple,
    )(input)
}

// Parse any actionable unit
fn actionable_unit(input: &str) -> IResult<&str, GetActionableUnit> {
    alt((tuple_unit, list_op_unit, single_unit))(input)
}

// Parse a complete get expression (chain of units separated by dots)
fn get_expr(input: &str) -> IResult<&str, GetExpr> {
    map(
        separated_list0(char('.'), actionable_unit),
        |units| GetExpr { units },
    )(input)
}

// Main parser function
pub fn parse_get_expr(input: &str) -> IResult<&str, ParsedGetExpr> {
    map(
        terminated(get_expr, space0),
        |expr| ParsedGetExpr { expr },
    )(input.trim())
}
