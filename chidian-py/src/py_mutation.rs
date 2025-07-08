use chidian_core::parser::{Path, PathSegment};
use chidian_core::mutation::{determine_container_type, expand_list_for_index, validate_mutation_path, ContainerType};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use pyo3::IntoPyObjectExt;

/// Mutate a PyObject by setting a value at the specified path
/// This function implements copy-on-write semantics
pub fn mut_traverse_or_create(
    py: Python<'_>,
    data: &Bound<'_, PyAny>,
    path: &Path,
    value: PyObject,
    strict: bool,
) -> PyResult<PyObject> {
    // Validate the path for mutation
    if let Err(e) = validate_mutation_path(path) {
        if strict {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()));
        } else {
            // Return unchanged data in non-strict mode
            return Ok(data.into_py_any(py).unwrap());
        }
    }

    // Deep copy the data to implement copy-on-write semantics
    let result = deep_copy_pyobject(py, data)?;
    let result_ref = result.bind(py);

    // Navigate to the target location, creating containers as needed
    let segments = &path.segments;

    // Navigate through all segments except the last
    let mut current_obj = result_ref.clone();
    for (i, segment) in segments[..segments.len() - 1].iter().enumerate() {
        current_obj = navigate_and_create_segment(py, &current_obj, segment, segments, i, strict)?;
    }
    let current = &current_obj;

    // Set the value at the final segment
    if let Some(final_segment) = segments.last() {
        set_final_value(py, current, final_segment, value, strict)?;
    }

    Ok(result)
}

/// Navigate through a single segment, creating containers as needed
fn navigate_and_create_segment<'py>(
    py: Python<'py>,
    current: &Bound<'py, PyAny>,
    segment: &PathSegment,
    segments: &[PathSegment],
    index: usize,
    strict: bool,
) -> PyResult<Bound<'py, PyAny>> {
    match segment {
        PathSegment::Key(key) => navigate_key_segment(py, current, key, segments, index, strict),
        PathSegment::Index(idx) => navigate_index_segment(py, current, *idx, segments, index, strict),
        _ => {
            // Wildcards, slices, and tuples should have been caught by validation
            Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unsupported segment type in mutation path",
            ))
        }
    }
}

/// Navigate through a key segment, creating dict containers as needed
fn navigate_key_segment<'py>(
    py: Python<'py>,
    current: &Bound<'py, PyAny>,
    key: &str,
    segments: &[PathSegment],
    index: usize,
    strict: bool,
) -> PyResult<Bound<'py, PyAny>> {
    // Ensure current is a dict
    let dict = if let Ok(d) = current.downcast::<PyDict>() {
        d
    } else {
        if strict {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                format!("Cannot traverse into non-dict at '{}'", key),
            ));
        } else {
            // In non-strict mode, we can't continue - return current
            return Ok(current.clone());
        }
    };

    // Determine what type of container we need for the next segment
    let container_type = determine_container_type(segments, index);

    // Ensure the key exists with the correct container type
    ensure_key_exists(py, dict, key, container_type, strict)?;

    // Get the value at the key
    if let Some(value) = dict.get_item(key)? {
        Ok(value)
    } else {
        Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Key '{}' should exist after creation", key),
        ))
    }
}

/// Navigate through an index segment, creating list containers as needed
fn navigate_index_segment<'py>(
    py: Python<'py>,
    current: &Bound<'py, PyAny>,
    idx: i32,
    segments: &[PathSegment],
    index: usize,
    strict: bool,
) -> PyResult<Bound<'py, PyAny>> {
    // Ensure current is a list
    let list = if let Ok(l) = current.downcast::<PyList>() {
        l
    } else {
        if strict {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Cannot index into non-list",
            ));
        } else {
            return Ok(current.clone());
        }
    };

    // Handle list expansion and negative indexing
    let target_idx = match expand_list_for_index(list.len(), idx, strict) {
        Ok(Some(i)) => i,
        Ok(None) => return Ok(current.clone()), // Error in non-strict mode
        Err(e) => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()));
        }
    };

    // Expand the list if necessary
    expand_list_to_index(py, list, target_idx)?;

    // Determine what type of container we need at this index
    let container_type = determine_container_type(segments, index);

    // Ensure the correct container type at the index
    ensure_index_container(py, list, target_idx, container_type, strict)?;

    // Get the value at the index
    Ok(list.get_item(target_idx)?)
}

/// Ensure a key exists in a dict with the correct container type
fn ensure_key_exists(
    py: Python<'_>,
    dict: &Bound<'_, PyDict>,
    key: &str,
    container_type: ContainerType,
    strict: bool,
) -> PyResult<()> {
    if let Some(existing) = dict.get_item(key)? {
        // Key exists - check if it has the correct type
        match container_type {
            ContainerType::List => {
                if existing.downcast::<PyList>().is_err() {
                    if strict {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Cannot index into dict at '{}' - expected list", key),
                        ));
                    } else {
                        // Replace with empty list
                        dict.set_item(key, PyList::empty(py))?;
                    }
                }
            }
            ContainerType::Dict => {
                if existing.downcast::<PyDict>().is_err() {
                    if strict {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Cannot access key in list at '{}' - expected dict", key),
                        ));
                    } else {
                        // Replace with empty dict
                        dict.set_item(key, PyDict::new(py))?;
                    }
                }
            }
        }
    } else {
        // Key doesn't exist - create the appropriate container
        match container_type {
            ContainerType::List => dict.set_item(key, PyList::empty(py))?,
            ContainerType::Dict => dict.set_item(key, PyDict::new(py))?,
        }
    }

    Ok(())
}

/// Expand a list to accommodate the given index
fn expand_list_to_index(py: Python<'_>, list: &Bound<'_, PyList>, target_idx: usize) -> PyResult<()> {
    while list.len() <= target_idx {
        list.append(py.None())?;
    }
    Ok(())
}

/// Ensure the correct container type at a list index
fn ensure_index_container(
    py: Python<'_>,
    list: &Bound<'_, PyList>,
    idx: usize,
    container_type: ContainerType,
    strict: bool,
) -> PyResult<()> {
    let current_item = list.get_item(idx)?;

    if current_item.is_none() {
        // Create the appropriate container
        match container_type {
            ContainerType::List => list.set_item(idx, PyList::empty(py))?,
            ContainerType::Dict => list.set_item(idx, PyDict::new(py))?,
        }
    } else {
        // Check if existing item has correct type
        match container_type {
            ContainerType::List => {
                if current_item.downcast::<PyList>().is_err() {
                    if strict {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Cannot traverse into non-list at index {}", idx),
                        ));
                    } else {
                        // Replace with empty list
                        list.set_item(idx, PyList::empty(py))?;
                    }
                }
            }
            ContainerType::Dict => {
                if current_item.downcast::<PyDict>().is_err() {
                    if strict {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                            format!("Cannot traverse into non-dict at index {}", idx),
                        ));
                    } else {
                        // Replace with empty dict
                        list.set_item(idx, PyDict::new(py))?;
                    }
                }
            }
        }
    }

    Ok(())
}

/// Set the final value at the target location
fn set_final_value(
    py: Python<'_>,
    current: &Bound<'_, PyAny>,
    segment: &PathSegment,
    value: PyObject,
    strict: bool,
) -> PyResult<()> {
    match segment {
        PathSegment::Key(key) => {
            if let Ok(dict) = current.downcast::<PyDict>() {
                dict.set_item(key, value)?;
            } else if strict {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Cannot set key '{}' on non-dict", key),
                ));
            }
        }
        PathSegment::Index(idx) => {
            if let Ok(list) = current.downcast::<PyList>() {
                let target_idx = match expand_list_for_index(list.len(), *idx, strict) {
                    Ok(Some(i)) => i,
                    Ok(None) => return Ok(()), // Error in non-strict mode
                    Err(e) => {
                        return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()));
                    }
                };

                // Expand the list if necessary
                expand_list_to_index(py, list, target_idx)?;

                // Set the value
                list.set_item(target_idx, value)?;
            } else if strict {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Cannot set index {} on non-list", idx),
                ));
            }
        }
        _ => {
            return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                "Unsupported segment type for final value",
            ));
        }
    }

    Ok(())
}

/// Deep copy a PyObject to implement copy-on-write semantics
fn deep_copy_pyobject(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<PyObject> {
    // Use Python's copy.deepcopy for now
    let copy_module = py.import("copy")?;
    let deepcopy = copy_module.getattr("deepcopy")?;
    let result = deepcopy.call1((obj,))?;
    Ok(result.into_py_any(py).unwrap())
}
