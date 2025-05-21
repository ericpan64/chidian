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

// TODO: Implement nom parser based on DSL above. The "Actionable Units" represent the semantic elements that will be operated on in `get`
pub enum GetActionableUnit {
    Single(String),
    ListOp(String),
    Tuple(Vec<GetActionableUnit>),
}

pub struct ParsedGetExpr {
    pub key: String,
    pub actionable_units: Vec<GetActionableUnit>,
}

use nom::{
    IResult,
    Parser,
    // ...
};
pub fn get_dsl_parser(key_str: &str) -> impl Fn(Span) -> IResult<&str, ParsedGetExpr> {
    // ...
}
