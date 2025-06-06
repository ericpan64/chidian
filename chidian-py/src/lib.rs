use pyo3::prelude::*;

mod py_traversal;

use chidian_core::parser::parse_path;
use py_traversal::{apply_functions, traverse_path, traverse_path_strict};

#[pyfunction]
#[pyo3(signature = (source, key, default=None, apply=None, strict=false))]
fn get(
    py: Python<'_>,
    source: &Bound<'_, PyAny>,
    key: &str,
    default: Option<&Bound<'_, PyAny>>,
    apply: Option<&Bound<'_, PyAny>>,
    strict: Option<bool>,
) -> PyResult<PyObject> {
    let strict = strict.unwrap_or(false);

    // Parse the path using chidian-core
    let path = match parse_path(key) {
        Ok((remaining, path)) if remaining.is_empty() => path,
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                "Invalid path syntax: {}",
                key
            )));
        }
    };

    // Traverse the path (always use flatten=false since it's removed)
    let result = if strict {
        match traverse_path_strict(py, source, &path, false) {
            Ok(val) => val,
            Err(e) => return Err(e),
        }
    } else {
        traverse_path(py, source, &path, false)?
    };

    // Handle default value first
    let mut final_result = result;
    if final_result.bind(py).is_none() {
        if let Some(default_val) = default {
            final_result = default_val.to_object(py);
        }
    }

    // Apply functions if provided (to the final result, including defaults)
    if let Some(functions) = apply {
        final_result = apply_functions(py, final_result, functions)?;
    }

    Ok(final_result)
}

/// A Python module implemented in Rust.
#[pymodule]
fn chidian_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get, m)?)?;
    Ok(())
}
