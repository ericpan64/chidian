use chidian_core::partials;

#[test]
fn test_do_fn() {
    let example_str = "Some String";
    let example_int = 100;

    // Test passing args
    fn some_function(first: &str, second: i32) -> String {
        format!("{}, {}!", first, second)
    }

    let str_param_fn = partials::do_fn(some_function, example_int);
    assert_eq!(some_function("Ma", example_int), str_param_fn("Ma"));

    // Test with standard library methods
    let replace_fn = partials::do_fn(str::replace, "S");
    assert_eq!(example_str.replace("S", "Z"), replace_fn(example_str, "Z"));

    let starts_with_fn = partials::do_fn(str::starts_with, "S");
    assert_eq!(example_str.starts_with("S"), starts_with_fn(example_str));
}

#[test]
fn test_echo() {
    let example_value = 42;
    let echo_fn = partials::echo::<(), _>(example_value);
    assert_eq!(example_value, echo_fn(()));
    assert_eq!(example_value, echo_fn("ignored"));
}

#[test]
fn test_arithmetic_operations() {
    // Test with integers
    let n = 100;
    
    let add_fn = partials::add(1, false);
    assert_eq!(n + 1, add_fn(n));
    
    let add_before_fn = partials::add(1, true);
    assert_eq!(1 + n, add_before_fn(n));
    
    let subtract_fn = partials::subtract(1, false);
    assert_eq!(n - 1, subtract_fn(n));
    
    let subtract_before_fn = partials::subtract(1, true);
    assert_eq!(1 - n, subtract_before_fn(n));
    
    let multiply_fn = partials::multiply(10, false);
    assert_eq!(n * 10, multiply_fn(n));
    
    let divide_fn = partials::divide(10, false);
    assert_eq!(n / 10, divide_fn(n));
    
    let divide_before_fn = partials::divide(10, true);
    assert_eq!(10 / n, divide_before_fn(n));

    // Test with vectors
    let v = vec![1, 2, 3];
    let add_vec_fn = partials::add(vec![4], false);
    assert_eq!(vec![1, 2, 3, 4], add_vec_fn(v.clone()));
    
    let add_vec_before_fn = partials::add(vec![4], true);
    assert_eq!(vec![4, 1, 2, 3], add_vec_before_fn(v.clone()));

    // Test with floats
    let f = 4.2;
    let multiply_float_fn = partials::multiply(3.0, false);
    assert_eq!(f * 3.0, multiply_float_fn(f));
    
    let multiply_float_before_fn = partials::multiply(3.0, true);
    assert_eq!(3.0 * f * f, multiply_float_before_fn(f * f));
}

#[test]
fn test_keep() {
    let v = vec![1, 2, 3, 4, 5];
    
    let keep_one_fn = partials::keep::<_, _>(1);
    assert_eq!(vec![1], keep_one_fn(v.clone()));
    
    let keep_more_fn = partials::keep::<_, _>(50);
    assert_eq!(v.clone(), keep_more_fn(v.clone()));
    
    // Test with array slice
    let arr = [1, 2, 3, 4, 5];
    assert_eq!(vec![1], keep_one_fn(&arr[..]));
}

#[test]
fn test_comparison_operations() {
    // Test equals and not_equal
    let value = std::collections::HashMap::from([("a", "b"), ("c", "d")]);
    let copied_value = value.clone();
    let example_key = "a";
    
    let equals_fn = partials::equals(copied_value.clone());
    assert_eq!(value == copied_value, equals_fn(value.clone()));
    
    let not_equal_fn = partials::not_equal(copied_value.clone());
    assert_eq!(value != copied_value, not_equal_fn(value.clone()));
    
    // Test numeric comparisons
    let x = 10;
    let y = 5;
    
    let gt_fn = partials::gt(y);
    assert_eq!(x > y, gt_fn(x));
    assert_eq!(y > y, gt_fn(y));
    
    let lt_fn = partials::lt(x);
    assert_eq!(y < x, lt_fn(y));
    assert_eq!(x < x, lt_fn(x));
    
    let gte_fn = partials::gte(y);
    assert_eq!(x >= y, gte_fn(x));
    assert_eq!(y >= y, gte_fn(y));
    
    let lte_fn = partials::lte(x);
    assert_eq!(y <= x, lte_fn(y));
    assert_eq!(x <= x, lte_fn(x));
}

#[test]
fn test_iterator_operations() {
    let example_list = vec!["a", "b", "c"];
    
    // Test map_to_vec
    let upper_fn = |s: &str| s.to_uppercase();
    let map_upper_fn = partials::map_to_vec(upper_fn);
    assert_eq!(vec!["A", "B", "C"], map_upper_fn(example_list.clone()));
    
    // Test filter_to_vec
    let equals_a = partials::equals("a");
    let filter_a_fn = partials::filter_to_vec(equals_a);
    assert_eq!(vec!["a"], filter_a_fn(example_list.clone()));
}