/// Parser for DSL expressions
/// 
/// Simplified grammar:
/// - get_expr = unit ("." unit)*
/// - unit = single | list_op | tuple
/// - single = identifier [index]?
/// - list_op = identifier? list_index
/// - tuple = "(" get_expr ("," get_expr)* ")"
/// - list_index = "[" ("*" | slice) "]"
/// - slice = number? ":" number?
/// - index = "[" number "]"
/// - identifier = [a-zA-Z_][a-zA-Z0-9_]*
/// - number = -?[0-9]+

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

/// A very simple DSL parser that handles basic path expressions
/// This implementation doesn't use any external parser libraries
pub fn parse_get_expr(input: &str) -> Result<((), ParsedGetExpr), String> {
    let input = input.trim();
    
    // Split the input into top-level units, handling parentheses properly
    let parts = split_respecting_parentheses(input, '.')?;
    let mut units = Vec::new();
    
    for part in parts {
        let part = part.as_str().trim();
        if part.is_empty() {
            continue;
        }
        
        // Check for tuple expression (foo, bar)
        if part.starts_with('(') && part.ends_with(')') {
            let tuple_content = &part[1..part.len()-1];
            let tuple_parts = split_respecting_parentheses(tuple_content, ',')?;
            
            let mut exprs = Vec::new();
            for tuple_part in tuple_parts {
                let tuple_part = tuple_part.as_str().trim();
                if tuple_part.is_empty() {
                    continue;
                }
                
                // Recursively parse each part of the tuple
                match parse_get_expr(tuple_part) {
                    Ok((_, parsed)) => exprs.push(parsed.expr),
                    Err(e) => return Err(format!("Error parsing tuple part '{}': {}", tuple_part, e)),
                }
            }
            
            if exprs.is_empty() {
                return Err("Empty tuple".to_string());
            }
            
            units.push(GetActionableUnit::Tuple(exprs));
            continue;
        }
        
        // Check for list operation or single with index
        if let Some(bracket_pos) = part.find('[') {
            let name_part = &part[0..bracket_pos];
            let index_part = &part[bracket_pos..];
            
            if !index_part.ends_with(']') {
                return Err(format!("Missing closing bracket in index: {}", index_part));
            }
            
            let index_content = &index_part[1..index_part.len()-1];
            
            // Star index [*]
            if index_content == "*" {
                let name = if name_part.is_empty() {
                    None
                } else {
                    Some(name_part.to_string())
                };
                units.push(GetActionableUnit::ListOp { name, index: IndexOp::Star });
                continue;
            }
            
            // Slice index [start:end]
            if index_content.contains(':') {
                let slice_parts: Vec<&str> = index_content.split(':').collect();
                if slice_parts.len() != 2 {
                    return Err(format!("Invalid slice syntax: {}", index_content));
                }
                
                let start = if slice_parts[0].trim().is_empty() {
                    None
                } else {
                    match slice_parts[0].trim().parse::<i32>() {
                        Ok(n) => Some(n),
                        Err(_) => return Err(format!("Invalid slice start: {}", slice_parts[0])),
                    }
                };
                
                let end = if slice_parts[1].trim().is_empty() {
                    None
                } else {
                    match slice_parts[1].trim().parse::<i32>() {
                        Ok(n) => Some(n),
                        Err(_) => return Err(format!("Invalid slice end: {}", slice_parts[1])),
                    }
                };
                
                let name = if name_part.is_empty() {
                    None
                } else {
                    Some(name_part.to_string())
                };
                
                units.push(GetActionableUnit::ListOp { name, index: IndexOp::Slice(start, end) });
                continue;
            }
            
            // Single index [42]
            match index_content.parse::<i32>() {
                Ok(n) => {
                    if name_part.is_empty() {
                        units.push(GetActionableUnit::ListOp { 
                            name: None,
                            index: IndexOp::Single(n)
                        });
                    } else {
                        units.push(GetActionableUnit::Single { 
                            name: name_part.to_string(),
                            index: Some(IndexOp::Single(n))
                        });
                    }
                },
                Err(_) => return Err(format!("Invalid index: {}", index_content)),
            }
            
            continue;
        }
        
        // Simple field access
        units.push(GetActionableUnit::Single { 
            name: part.to_string(),
            index: None
        });
    }
    
    if units.is_empty() {
        return Err("Empty expression".to_string());
    }
    
    Ok(((), ParsedGetExpr { expr: GetExpr { units } }))
}

/// Split a string by a delimiter while respecting parentheses
fn split_respecting_parentheses(input: &str, delimiter: char) -> Result<Vec<String>, String> {
    let mut parts = Vec::new();
    let mut current = String::new();
    let mut paren_depth = 0;
    let mut chars = input.chars().peekable();
    
    while let Some(ch) = chars.next() {
        match ch {
            '(' => {
                paren_depth += 1;
                current.push(ch);
            },
            ')' => {
                paren_depth -= 1;
                if paren_depth < 0 {
                    return Err("Unmatched closing parenthesis".to_string());
                }
                current.push(ch);
            },
            ch if ch == delimiter && paren_depth == 0 => {
                parts.push(current.trim().to_string());
                current.clear();
            },
            _ => {
                current.push(ch);
            }
        }
    }
    
    if paren_depth != 0 {
        return Err("Unmatched opening parenthesis".to_string());
    }
    
    if !current.trim().is_empty() {
        parts.push(current.trim().to_string());
    }
    
    Ok(parts)
}
