use chidian_core::dicts::dsl_parser::{parse_get_expr, GetActionableUnit, IndexOp, GetExpr, ParsedGetExpr};

#[test]
fn test_simple_identifier() {
    let result = parse_get_expr("users");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 1);
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert!(index.is_none());
        }
        _ => panic!("Expected Single unit"),
    }
}

#[test]
fn test_identifier_with_index() {
    let result = parse_get_expr("users[0]");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 1);
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert_eq!(index, &Some(IndexOp::Single(0)));
        }
        _ => panic!("Expected Single unit"),
    }
}

#[test]
fn test_negative_index() {
    let result = parse_get_expr("users[-1]");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert_eq!(index, &Some(IndexOp::Single(-1)));
        }
        _ => panic!("Expected Single unit"),
    }
}

#[test]
fn test_star_index() {
    let result = parse_get_expr("users[*]");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    match &parsed.expr.units[0] {
        GetActionableUnit::ListOp { name, index } => {
            assert_eq!(name, &Some("users".to_string()));
            assert_eq!(index, &IndexOp::Star);
        }
        _ => panic!("Expected ListOp unit"),
    }
}

#[test]
fn test_slice_index() {
    let result = parse_get_expr("users[1:3]");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    match &parsed.expr.units[0] {
        GetActionableUnit::ListOp { name, index } => {
            assert_eq!(name, &Some("users".to_string()));
            assert_eq!(index, &IndexOp::Slice(Some(1), Some(3)));
        }
        _ => panic!("Expected ListOp unit"),
    }
}

#[test]
fn test_open_slice() {
    let result = parse_get_expr("users[1:]");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    match &parsed.expr.units[0] {
        GetActionableUnit::ListOp { name, index } => {
            assert_eq!(name, &Some("users".to_string()));
            assert_eq!(index, &IndexOp::Slice(Some(1), None));
        }
        _ => panic!("Expected ListOp unit"),
    }
}

#[test]
fn test_chained_access() {
    let result = parse_get_expr("users[0].name");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 2);
    
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert_eq!(index, &Some(IndexOp::Single(0)));
        }
        _ => panic!("Expected Single unit"),
    }
    
    match &parsed.expr.units[1] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "name");
            assert!(index.is_none());
        }
        _ => panic!("Expected Single unit"),
    }
}

#[test]
fn test_tuple_simple() {
    let result = parse_get_expr("(name, age)");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 1);
    
    match &parsed.expr.units[0] {
        GetActionableUnit::Tuple(exprs) => {
            assert_eq!(exprs.len(), 2);
            
            // Check first expression: name
            assert_eq!(exprs[0].units.len(), 1);
            match &exprs[0].units[0] {
                GetActionableUnit::Single { name, index } => {
                    assert_eq!(name, "name");
                    assert!(index.is_none());
                }
                _ => panic!("Expected Single unit"),
            }
            
            // Check second expression: age
            assert_eq!(exprs[1].units.len(), 1);
            match &exprs[1].units[0] {
                GetActionableUnit::Single { name, index } => {
                    assert_eq!(name, "age");
                    assert!(index.is_none());
                }
                _ => panic!("Expected Single unit"),
            }
        }
        _ => panic!("Expected Tuple unit"),
    }
}

#[test]
fn test_complex_expression() {
    let result = parse_get_expr("users[0].(name, profile.age)");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 2);
    
    // First unit: users[0]
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert_eq!(index, &Some(IndexOp::Single(0)));
        }
        _ => panic!("Expected Single unit"),
    }
    
    // Second unit: (name, profile.age)
    match &parsed.expr.units[1] {
        GetActionableUnit::Tuple(exprs) => {
            assert_eq!(exprs.len(), 2);
            
            // First tuple element: name
            assert_eq!(exprs[0].units.len(), 1);
            match &exprs[0].units[0] {
                GetActionableUnit::Single { name, index } => {
                    assert_eq!(name, "name");
                    assert!(index.is_none());
                }
                _ => panic!("Expected Single unit"),
            }
            
            // Second tuple element: profile.age
            assert_eq!(exprs[1].units.len(), 2);
            match &exprs[1].units[0] {
                GetActionableUnit::Single { name, index } => {
                    assert_eq!(name, "profile");
                    assert!(index.is_none());
                }
                _ => panic!("Expected Single unit"),
            }
            match &exprs[1].units[1] {
                GetActionableUnit::Single { name, index } => {
                    assert_eq!(name, "age");
                    assert!(index.is_none());
                }
                _ => panic!("Expected Single unit"),
            }
        }
        _ => panic!("Expected Tuple unit"),
    }
}

#[test]
fn test_whitespace_handling() {
    let result = parse_get_expr(" users[0].name ");
    assert!(result.is_ok());
    let (remaining, parsed) = result.unwrap();
    assert_eq!(remaining, ());
    assert_eq!(parsed.expr.units.len(), 2);
    
    match &parsed.expr.units[0] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "users");
            assert_eq!(index, &Some(IndexOp::Single(0)));
        }
        _ => panic!("Expected Single unit"),
    }
    
    match &parsed.expr.units[1] {
        GetActionableUnit::Single { name, index } => {
            assert_eq!(name, "name");
            assert!(index.is_none());
        }
        _ => panic!("Expected Single unit"),
    }
}