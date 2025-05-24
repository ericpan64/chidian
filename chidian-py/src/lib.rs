use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList, PyTuple, PyAny};
use serde_json::Value;
use ::chidian_core::{JsonContainer, flatten_sequence};
use ::chidian_core::dicts::get as core_get;

/// Get a value from a nested data structure using a key path.
/// 
/// Supports dot notation, array indexing, slicing, wildcards, and tuple extraction.
#[pyfunction]
#[pyo3(signature = (source, key, default=None, apply=None, only_if=None, _drop_level=None, flatten=false, strict=None))]
fn get(
    py: Python,
    source: Bound<'_, PyAny>,
    key: &str,
    default: Option<Bound<'_, PyAny>>,
    apply: Option<Bound<'_, PyAny>>,
    only_if: Option<Bound<'_, PyAny>>,
    _drop_level: Option<Bound<'_, PyAny>>,
    flatten: bool,
    strict: Option<bool>,
) -> PyResult<PyObject> {
    // Convert Python object to JSON Value
    let json_value = python_to_json(py, &source)?;
    
    // Convert to JsonContainer
    let container = match JsonContainer::try_from(json_value) {
        Ok(container) => container,
        Err(_) => {
            // If it's not a container, try to make it one by wrapping in an object
            return handle_non_container_source(py, &source, key, default.as_ref());
        }
    };
    
    // Determine effective strict mode
    let effective_strict = match strict {
        Some(s) => s,
        None => false, // Default to false for now
    };
    
    // Call the core Rust get function
    let result = match core_get(container, key, None) {
        Ok(mapping_context) => mapping_context.data,
        Err(_) => {
            if effective_strict {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Key '{}' not found in source", key)
                ));
            }
            return Ok(convert_option_to_python(py, default.as_ref())?);
        }
    };
    
    // Apply only_if check
    if let Some(only_if_func) = only_if {
        let py_result = json_to_python(py, &result)?;
        let check_result = only_if_func.call1((py_result,))?;
        if !check_result.is_truthy()? {
            return Ok(py.None());
        }
    }
    
    // Apply transformation functions
    let mut processed_result = result;
    if let Some(apply_func) = apply {
        processed_result = apply_transformations(py, &processed_result, &apply_func)?;
    }
    
    // Apply flattening if requested
    if flatten {
        processed_result = flatten_sequence(processed_result);
    }
    
    // Convert back to Python
    json_to_python(py, &processed_result)
}

fn handle_non_container_source(
    py: Python,
    source: &Bound<'_, PyAny>,
    key: &str,
    default: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    // For simple key access on a dict-like object
    if key.contains('.') || key.contains('[') || key.contains('(') {
        return Ok(convert_option_to_python(py, default)?);
    }
    
    // Try direct attribute/key access
    if let Ok(dict) = source.downcast::<PyDict>() {
        if let Some(value) = dict.get_item(key)? {
            return Ok(value.into_py(py));
        }
    }
    
    Ok(convert_option_to_python(py, default)?)
}

fn apply_transformations(
    py: Python,
    result: &Value,
    apply: &Bound<'_, PyAny>,
) -> PyResult<Value> {
    let py_result = json_to_python(py, result)?;
    
    // Check if apply is a list/tuple of functions
    if let Ok(sequence) = apply.downcast::<PyList>() {
        let mut current = py_result;
        for func in sequence.iter() {
            if current.bind(py).is_none() {
                break; // Short-circuit on None
            }
            current = func.call1((current,))?.into();
        }
        python_to_json(py, &current.bind(py))
    } else if let Ok(sequence) = apply.downcast::<PyTuple>() {
        let mut current = py_result;
        for func in sequence.iter() {
            if current.bind(py).is_none() {
                break; // Short-circuit on None
            }
            current = func.call1((current,))?.into();
        }
        python_to_json(py, &current.bind(py))
    } else {
        // Single function
        let transformed = apply.call1((py_result,))?;
        python_to_json(py, &transformed)
    }
}

fn convert_option_to_python(py: Python, option: Option<&Bound<'_, PyAny>>) -> PyResult<PyObject> {
    match option {
        Some(value) => Ok(value.clone().into_py(py)),
        None => Ok(py.None()),
    }
}

fn python_to_json(py: Python, obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        Ok(Value::Null)
    } else if let Ok(b) = obj.extract::<bool>() {
        Ok(Value::Bool(b))
    } else if let Ok(i) = obj.extract::<i64>() {
        Ok(Value::Number(i.into()))
    } else if let Ok(f) = obj.extract::<f64>() {
        if let Some(num) = serde_json::Number::from_f64(f) {
            Ok(Value::Number(num))
        } else {
            Ok(Value::Null)
        }
    } else if let Ok(s) = obj.extract::<String>() {
        Ok(Value::String(s))
    } else if let Ok(list) = obj.downcast::<PyList>() {
        let mut vec = Vec::new();
        for item in list.iter() {
            vec.push(python_to_json(py, &item)?);
        }
        Ok(Value::Array(vec))
    } else if let Ok(tuple) = obj.downcast::<PyTuple>() {
        let mut vec = Vec::new();
        for item in tuple.iter() {
            vec.push(python_to_json(py, &item)?);
        }
        Ok(Value::Array(vec))
    } else if let Ok(dict) = obj.downcast::<PyDict>() {
        let mut map = serde_json::Map::new();
        for (key, value) in dict.iter() {
            let key_str = key.extract::<String>()?;
            map.insert(key_str, python_to_json(py, &value)?);
        }
        Ok(Value::Object(map))
    } else {
        // Try to convert to string as fallback
        let repr = obj.str()?.extract::<String>()?;
        Ok(Value::String(repr))
    }
}

fn json_to_python(py: Python, value: &Value) -> PyResult<PyObject> {
    match value {
        Value::Null => Ok(py.None()),
        Value::Bool(b) => Ok(b.into_py(py)),
        Value::Number(n) => {
            if let Some(i) = n.as_i64() {
                Ok(i.into_py(py))
            } else if let Some(f) = n.as_f64() {
                Ok(f.into_py(py))
            } else {
                Ok(py.None())
            }
        },
        Value::String(s) => Ok(s.into_py(py)),
        Value::Array(arr) => {
            let py_list = PyList::empty(py);
            for item in arr {
                py_list.append(json_to_python(py, item)?)?;
            }
            Ok(py_list.into_py(py))
        },
        Value::Object(obj) => {
            // Check if this is a tuple marker
            if let (Some(Value::Bool(true)), Some(Value::Array(values))) = 
                (obj.get("__tuple__"), obj.get("values")) {
                // Convert to Python tuple
                let py_items: PyResult<Vec<PyObject>> = values.iter()
                    .map(|v| json_to_python(py, v))
                    .collect();
                let py_tuple = PyTuple::new(py, py_items?)?;
                Ok(py_tuple.into_py(py))
            } else {
                // Regular object
                let py_dict = PyDict::new(py);
            for (key, value) in obj {
                py_dict.set_item(key, json_to_python(py, value)?)?;
            }
            Ok(py_dict.into_py(py))
            }
        }
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn chidian(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(get, m)?)?;
    Ok(())
}
