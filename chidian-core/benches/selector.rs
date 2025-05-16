use criterion::{criterion_group, criterion_main, Criterion, BenchmarkId};
use chidian_core::{get, get_selector, Selector};
use serde_json::json;

pub fn selector_benchmarks(c: &mut Criterion) {
    let mut group = c.benchmark_group("selector");
    let data = json!({
        "users": [
            {"name": "Alice", "age": 30, "email": "alice@example.com", "roles": ["admin", "editor"]},
            {"name": "Bob", "age": 25, "email": "bob@example.com", "roles": ["user"]},
            {"name": "Charlie", "age": 35, "email": "charlie@example.com", "roles": ["editor"]}
        ],
        "config": {
            "version": "1.0",
            "features": ["auth", "api", "ui"],
            "limits": {
                "maxUsers": 100,
                "maxRoles": 5
            }
        }
    });
    
    // Simple path selectors
    let simple_selector = "config.version";
    let array_selector = "users[1].name";
    let complex_selector = "users[*].roles[0]";
    let slice_selector = "users[0:2].name";
    
    // Compare raw parsing vs cached access for simple selector
    group.bench_with_input(BenchmarkId::new("parse_raw", "simple"), &simple_selector, |b, selector| {
        b.iter(|| {
            let sel = Selector::parse(selector).unwrap();
            let _ = get_selector(&data, &sel, &[]).unwrap();
        })
    });
    
    group.bench_with_input(BenchmarkId::new("cached", "simple"), &simple_selector, |b, selector| {
        b.iter(|| {
            let _ = get(&data, selector, &[]).unwrap();
        })
    });
    
    // Compare raw parsing vs cached access for array selector
    group.bench_with_input(BenchmarkId::new("parse_raw", "array"), &array_selector, |b, selector| {
        b.iter(|| {
            let sel = Selector::parse(selector).unwrap();
            let _ = get_selector(&data, &sel, &[]).unwrap();
        })
    });
    
    group.bench_with_input(BenchmarkId::new("cached", "array"), &array_selector, |b, selector| {
        b.iter(|| {
            let _ = get(&data, selector, &[]).unwrap();
        })
    });
    
    // Compare raw parsing vs cached access for complex selector (wildcard)
    group.bench_with_input(BenchmarkId::new("parse_raw", "complex"), &complex_selector, |b, selector| {
        b.iter(|| {
            let sel = Selector::parse(selector).unwrap();
            let _ = get_selector(&data, &sel, &[]).unwrap();
        })
    });
    
    group.bench_with_input(BenchmarkId::new("cached", "complex"), &complex_selector, |b, selector| {
        b.iter(|| {
            let _ = get(&data, selector, &[]).unwrap();
        })
    });
    
    // Compare raw parsing vs cached access for slice selector
    group.bench_with_input(BenchmarkId::new("parse_raw", "slice"), &slice_selector, |b, selector| {
        b.iter(|| {
            let sel = Selector::parse(selector).unwrap();
            let _ = get_selector(&data, &sel, &[]).unwrap();
        })
    });
    
    group.bench_with_input(BenchmarkId::new("cached", "slice"), &slice_selector, |b, selector| {
        b.iter(|| {
            let _ = get(&data, selector, &[]).unwrap();
        })
    });
    
    group.finish();
}

criterion_group!(benches, selector_benchmarks);
criterion_main!(benches); 