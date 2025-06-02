use chidian_core::parser::{Path, PathSegment};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple};

// Apply a chain of functions to a value
pub fn apply_functions(
    py: Python<'_>,
    value: PyObject,
    functions: &Bound<'_, PyAny>,
) -> PyResult<PyObject> {
    let mut current = value;

    // Check if it's a single function or a list
    if functions.downcast::<PyList>().is_ok() {
        let func_list = functions.downcast::<PyList>()?;
        for func in func_list.iter() {
            match func.call1((current,)) {
                Ok(result) => current = result.to_object(py),
                Err(_) => return Ok(py.None()),
            }
        }
    } else {
        // Single function
        match functions.call1((current,)) {
            Ok(result) => current = result.to_object(py),
            Err(_) => return Ok(py.None()),
        }
    }

    Ok(current)
}

// Traverse the data structure according to the path (strict version)
pub fn traverse_path_strict(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    path: &Path,
    flatten: bool,
) -> PyResult<PyObject> {
    let mut current = vec![data.to_object(py)];

    for segment in &path.segments {
        let mut next = Vec::new();

        for item in current {
            let item_ref = item.bind(py);

            match segment {
                PathSegment::Key(key) => {
                    if let Ok(dict) = item_ref.downcast::<PyDict>() {
                        if let Some(value) = dict.get_item(key)? {
                            next.push(value.to_object(py));
                        } else {
                            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                                "Key '{}' not found",
                                key
                            )));
                        }
                    } else if let Ok(list) = item_ref.downcast::<PyList>() {
                        // If we have a list and trying to access a key, apply to each element
                        for list_item in list {
                            if let Ok(dict) = list_item.downcast::<PyDict>() {
                                if let Some(value) = dict.get_item(key)? {
                                    next.push(value.to_object(py));
                                } else {
                                    return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                        format!("Key '{}' not found in list element", key),
                                    ));
                                }
                            } else {
                                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                                    "Expected dict in list but got different type",
                                ));
                            }
                        }
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Expected dict but got different type",
                        ));
                    }
                }
                PathSegment::Index(idx) => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        let len = list.len() as i32;
                        let actual_idx = if *idx < 0 { len + idx } else { *idx };

                        if actual_idx >= 0 && actual_idx < len {
                            next.push(list.get_item(actual_idx as usize)?.to_object(py));
                        } else {
                            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(format!(
                                "Index {} out of range",
                                idx
                            )));
                        }
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Expected list but got different type",
                        ));
                    }
                }
                PathSegment::Slice(start, end) => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        let len = list.len() as i32;

                        // Handle negative indices Python-style
                        let start_idx = match start {
                            Some(s) if *s < 0 => (len + s).max(0) as usize,
                            Some(s) => (*s).min(len).max(0) as usize,
                            None => 0,
                        };

                        let end_idx = match end {
                            Some(e) if *e < 0 => (len + e).max(0) as usize,
                            Some(e) => (*e).min(len).max(0) as usize,
                            None => len as usize,
                        };

                        let slice_items: Vec<PyObject> = if start_idx <= end_idx {
                            (start_idx..end_idx)
                                .filter_map(|i| list.get_item(i).ok())
                                .map(|item| item.to_object(py))
                                .collect()
                        } else {
                            Vec::new()
                        };

                        next.push(PyList::new(py, slice_items)?.to_object(py));
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Expected list but got different type",
                        ));
                    }
                }
                PathSegment::Wildcard => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        for list_item in list {
                            next.push(list_item.to_object(py));
                        }
                    } else {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            "Expected list but got different type",
                        ));
                    }
                }
                PathSegment::Tuple(paths) => {
                    let mut tuple_items = Vec::new();

                    for tuple_path in paths {
                        let result = traverse_path_strict(py, item_ref, tuple_path, false)?;
                        tuple_items.push(result);
                    }

                    next.push(PyTuple::new(py, tuple_items)?.to_object(py));
                }
            }
        }

        current = next;
    }

    // Handle flattening if needed
    if flatten {
        let mut flattened = Vec::new();
        for item in &current {
            let item_ref = item.bind(py);
            if let Ok(list) = item_ref.downcast::<PyList>() {
                for subitem in list {
                    if let Ok(sublist) = subitem.downcast::<PyList>() {
                        for subsubitem in sublist {
                            flattened.push(subsubitem.to_object(py));
                        }
                    } else {
                        flattened.push(subitem.to_object(py));
                    }
                }
            } else {
                flattened.push(item.clone_ref(py));
            }
        }
        return Ok(PyList::new(py, flattened)?.to_object(py));
    }

    // Return the result
    if current.len() == 1 {
        Ok(current[0].clone_ref(py))
    } else {
        Ok(PyList::new(py, current)?.to_object(py))
    }
}

// Traverse the data structure according to the path
pub fn traverse_path(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    path: &Path,
    flatten: bool,
) -> PyResult<PyObject> {
    let mut current = vec![data.to_object(py)];

    for segment in &path.segments {
        let mut next = Vec::new();

        for item in current {
            let item_ref = item.bind(py);

            match segment {
                PathSegment::Key(key) => {
                    if let Ok(dict) = item_ref.downcast::<PyDict>() {
                        if let Some(value) = dict.get_item(key)? {
                            next.push(value.to_object(py));
                        } else {
                            next.push(py.None());
                        }
                    } else if let Ok(list) = item_ref.downcast::<PyList>() {
                        // If we have a list and trying to access a key, apply to each element
                        for list_item in list {
                            if let Ok(dict) = list_item.downcast::<PyDict>() {
                                if let Some(value) = dict.get_item(key)? {
                                    next.push(value.to_object(py));
                                } else {
                                    next.push(py.None());
                                }
                            } else {
                                next.push(py.None());
                            }
                        }
                    } else {
                        next.push(py.None());
                    }
                }
                PathSegment::Index(idx) => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        let len = list.len() as i32;
                        let actual_idx = if *idx < 0 { len + idx } else { *idx };

                        if actual_idx >= 0 && actual_idx < len {
                            next.push(list.get_item(actual_idx as usize)?.to_object(py));
                        } else {
                            next.push(py.None());
                        }
                    } else {
                        next.push(py.None());
                    }
                }
                PathSegment::Slice(start, end) => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        let len = list.len() as i32;

                        // Handle negative indices Python-style
                        let start_idx = match start {
                            Some(s) if *s < 0 => (len + s).max(0) as usize,
                            Some(s) => (*s).min(len).max(0) as usize,
                            None => 0,
                        };

                        let end_idx = match end {
                            Some(e) if *e < 0 => (len + e).max(0) as usize,
                            Some(e) => (*e).min(len).max(0) as usize,
                            None => len as usize,
                        };

                        let slice_items: Vec<PyObject> = if start_idx <= end_idx {
                            (start_idx..end_idx)
                                .filter_map(|i| list.get_item(i).ok())
                                .map(|item| item.to_object(py))
                                .collect()
                        } else {
                            Vec::new()
                        };

                        next.push(PyList::new(py, slice_items)?.to_object(py));
                    } else {
                        next.push(py.None());
                    }
                }
                PathSegment::Wildcard => {
                    if let Ok(list) = item_ref.downcast::<PyList>() {
                        for list_item in list {
                            next.push(list_item.to_object(py));
                        }
                    } else {
                        next.push(py.None());
                    }
                }
                PathSegment::Tuple(paths) => {
                    let mut tuple_items = Vec::new();

                    for tuple_path in paths {
                        let result = traverse_path(py, item_ref, tuple_path, false)?;
                        tuple_items.push(result);
                    }

                    next.push(PyTuple::new(py, tuple_items)?.to_object(py));
                }
            }
        }

        current = next;
    }

    // Handle flattening if needed
    if flatten {
        let mut flattened = Vec::new();
        for item in &current {
            let item_ref = item.bind(py);
            if let Ok(list) = item_ref.downcast::<PyList>() {
                for subitem in list {
                    if let Ok(sublist) = subitem.downcast::<PyList>() {
                        for subsubitem in sublist {
                            flattened.push(subsubitem.to_object(py));
                        }
                    } else {
                        flattened.push(subitem.to_object(py));
                    }
                }
            } else {
                flattened.push(item.clone_ref(py));
            }
        }
        return Ok(PyList::new(py, flattened)?.to_object(py));
    }

    // Return the result
    if current.len() == 1 {
        Ok(current[0].clone_ref(py))
    } else {
        Ok(PyList::new(py, current)?.to_object(py))
    }
}
