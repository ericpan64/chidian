use pyo3::prelude::*;
use pyo3::types::PyAny;
use serde::{Deserialize, Serialize};

/// Core seed data structures for chidian transformations
/// These represent special values that control transformation behavior

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum Seed {
    /// Drop values at various levels of nesting
    Drop(DropLevel),
    /// Keep a specific value regardless of source data
    Keep(KeepValue),
    // Future seed types will be added here:
    // Merge(MergeSpec),
    // Flatten(FlattenSpec),
    // Coalesce(CoalesceSpec),
    // Split(SplitSpec),
    // Case(CaseSpec),
}

/// Hierarchical drop levels for removing values during transformation
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum DropLevel {
    /// Drop the current object/value
    ThisObject = -1,
    /// Drop the parent container
    Parent = -2,
    /// Drop the grandparent container
    GrandParent = -3,
    /// Drop the great-grandparent container
    GreatGrandParent = -4,
}

/// Wrapper for values that should be kept regardless of source data
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct KeepValue {
    /// The value to keep
    pub value: serde_json::Value,
}

/// PyO3 bindings for Python integration
#[pyclass(name = "SeedDrop")]
#[derive(Clone)]
pub struct PySeedDrop {
    level: DropLevel,
}

#[pymethods]
impl PySeedDrop {
    #[new]
    fn new(level: i32) -> PyResult<Self> {
        let drop_level = match level {
            -1 => DropLevel::ThisObject,
            -2 => DropLevel::Parent,
            -3 => DropLevel::GrandParent,
            -4 => DropLevel::GreatGrandParent,
            _ => {
                return Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
                    format!("Invalid drop level: {}. Must be -1, -2, -3, or -4", level)
                ));
            }
        };
        Ok(PySeedDrop { level: drop_level })
    }

    /// Get the drop level as an integer
    #[getter]
    fn level(&self) -> i32 {
        self.level.clone() as i32
    }

    /// Process method for compatibility with Python API
    /// Returns self since actual processing happens in Piper
    fn process(&self, _data: &Bound<'_, PyAny>, _context: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PySeedDrop>> {
        Python::with_gil(|py| Ok(Py::new(py, self.clone())?))
    }

    /// String representation
    fn __repr__(&self) -> String {
        format!("SeedDrop(level={})", self.level.clone() as i32)
    }

    /// Equality comparison
    fn __eq__(&self, other: &PySeedDrop) -> bool {
        self.level == other.level
    }
}

#[pyclass(name = "SeedKeep")]
pub struct PySeedKeep {
    value: PyObject,
}

#[pymethods]
impl PySeedKeep {
    #[new]
    fn new(value: PyObject) -> Self {
        PySeedKeep { value }
    }

    /// Get the kept value
    #[getter]
    fn value(&self, py: Python<'_>) -> PyObject {
        self.value.clone_ref(py)
    }

    /// Process method for compatibility with Python API
    /// Returns the wrapped value
    fn process(&self, py: Python<'_>, _data: &Bound<'_, PyAny>, _context: Option<&Bound<'_, PyAny>>) -> PyObject {
        self.value.clone_ref(py)
    }

    /// String representation
    fn __repr__(&self, py: Python<'_>) -> PyResult<String> {
        let value_repr = self.value.bind(py).repr()?;
        Ok(format!("SeedKeep(value={})", value_repr))
    }

    /// Equality comparison
    fn __eq__(&self, other: &PySeedKeep, py: Python<'_>) -> PyResult<bool> {
        let result = self.value.bind(py).eq(other.value.bind(py))?;
        Ok(result)
    }
}

impl Seed {
    /// Convert from Python drop level integer to Rust enum
    pub fn from_drop_level(level: i32) -> Result<Self, String> {
        match level {
            -1 => Ok(Seed::Drop(DropLevel::ThisObject)),
            -2 => Ok(Seed::Drop(DropLevel::Parent)),
            -3 => Ok(Seed::Drop(DropLevel::GrandParent)),
            -4 => Ok(Seed::Drop(DropLevel::GreatGrandParent)),
            _ => Err(format!("Invalid drop level: {}", level)),
        }
    }

    /// Create a Keep seed from a JSON value
    pub fn from_keep_value(value: serde_json::Value) -> Self {
        Seed::Keep(KeepValue { value })
    }

    /// Check if this seed is a Drop type
    pub fn is_drop(&self) -> bool {
        matches!(self, Seed::Drop(_))
    }

    /// Check if this seed is a Keep type
    pub fn is_keep(&self) -> bool {
        matches!(self, Seed::Keep(_))
    }

    /// Get the drop level if this is a Drop seed
    pub fn drop_level(&self) -> Option<&DropLevel> {
        match self {
            Seed::Drop(level) => Some(level),
            _ => None,
        }
    }

    /// Get the keep value if this is a Keep seed
    pub fn keep_value(&self) -> Option<&serde_json::Value> {
        match self {
            Seed::Keep(keep) => Some(&keep.value),
            _ => None,
        }
    }
}

impl DropLevel {
    /// Get the numeric level for this drop level
    pub fn level(&self) -> i32 {
        self.clone() as i32
    }

    /// Create from integer level
    pub fn from_level(level: i32) -> Result<Self, String> {
        match level {
            -1 => Ok(DropLevel::ThisObject),
            -2 => Ok(DropLevel::Parent),
            -3 => Ok(DropLevel::GrandParent),
            -4 => Ok(DropLevel::GreatGrandParent),
            _ => Err(format!("Invalid drop level: {}", level)),
        }
    }
}

impl KeepValue {
    /// Create a new KeepValue
    pub fn new(value: serde_json::Value) -> Self {
        KeepValue { value }
    }

    /// Get the wrapped value
    pub fn value(&self) -> &serde_json::Value {
        &self.value
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    #[test]
    fn test_drop_levels() {
        assert_eq!(DropLevel::ThisObject.level(), -1);
        assert_eq!(DropLevel::Parent.level(), -2);
        assert_eq!(DropLevel::GrandParent.level(), -3);
        assert_eq!(DropLevel::GreatGrandParent.level(), -4);
    }

    #[test]
    fn test_drop_level_from_int() {
        assert_eq!(DropLevel::from_level(-1).unwrap(), DropLevel::ThisObject);
        assert_eq!(DropLevel::from_level(-2).unwrap(), DropLevel::Parent);
        assert_eq!(DropLevel::from_level(-3).unwrap(), DropLevel::GrandParent);
        assert_eq!(DropLevel::from_level(-4).unwrap(), DropLevel::GreatGrandParent);
        assert!(DropLevel::from_level(-5).is_err());
        assert!(DropLevel::from_level(0).is_err());
    }

    #[test]
    fn test_seed_creation() {
        let drop_seed = Seed::from_drop_level(-1).unwrap();
        assert!(drop_seed.is_drop());
        assert!(!drop_seed.is_keep());
        assert_eq!(drop_seed.drop_level().unwrap(), &DropLevel::ThisObject);

        let keep_seed = Seed::from_keep_value(json!("test"));
        assert!(keep_seed.is_keep());
        assert!(!keep_seed.is_drop());
        assert_eq!(keep_seed.keep_value().unwrap(), &json!("test"));
    }

    #[test]
    fn test_keep_value() {
        let keep = KeepValue::new(json!({"key": "value"}));
        assert_eq!(keep.value(), &json!({"key": "value"}));
    }

    #[test]
    fn test_serialization() {
        let drop_seed = Seed::Drop(DropLevel::Parent);
        let json_str = serde_json::to_string(&drop_seed).unwrap();
        let deserialized: Seed = serde_json::from_str(&json_str).unwrap();
        assert_eq!(drop_seed, deserialized);

        let keep_seed = Seed::Keep(KeepValue::new(json!("test")));
        let json_str = serde_json::to_string(&keep_seed).unwrap();
        let deserialized: Seed = serde_json::from_str(&json_str).unwrap();
        assert_eq!(keep_seed, deserialized);
    }
}
