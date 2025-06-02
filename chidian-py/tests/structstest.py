"""
Shared test models for all test files.

Consolidates Pydantic models used across the test suite to avoid duplication
and provide consistent test data structures. This prevents inline model
definitions scattered across test files and makes it easier to reason about
test data structures across the entire test suite.
"""

from typing import Optional

from pydantic import BaseModel

# =============================================================================
# Medical Domain Models (Patient/Observation)
# =============================================================================


class Patient(BaseModel):
    """Sample Patient model for testing transformations."""

    id: str
    name: str
    active: bool
    age: Optional[int] = None


class Observation(BaseModel):
    """Sample Observation model for testing transformations."""

    subject_ref: str
    performer: str
    status: Optional[str] = None


# =============================================================================
# Basic Processing Models
# =============================================================================


class SourceData(BaseModel):
    """Generic source data container."""

    data: dict = {}


class ProcessedData(BaseModel):
    """Generic processed data with standard fields."""

    patient_id: str
    is_active: bool
    status: str


class PersonSource(BaseModel):
    """Source model for person-based transformations."""

    firstName: str
    lastName: str
    status: str
    codes: list[str]
    address: str


class PersonTarget(BaseModel):
    """Target model for person-based transformations."""

    name: str
    status_display: str
    all_codes: str
    city: str
    backup_name: str


# =============================================================================
# Consolidated Inline Models from Test Files
# =============================================================================


class SimpleTarget(BaseModel):
    """Basic target model for seed processing tests."""

    patient_id: str
    is_active: bool


class KeepTestTarget(BaseModel):
    """Target model for testing KEEP object processing."""

    processed_value: str
    regular_value: str


class SourceModel(BaseModel):
    """Simple source model for basic mapping tests."""

    value: str


class TargetModel(BaseModel):
    """Simple target model for basic mapping tests."""

    result: str


class BasicSource(BaseModel):
    """Generic source model for validation tests."""

    id: str


class BasicTarget(BaseModel):
    """Generic target model for validation tests."""

    id: str
    required_field: str


class BasicSourceWithName(BaseModel):
    """Source model with id and name fields."""

    id: str
    name: str


class BasicTargetWithPersonId(BaseModel):
    """Target model with person_id and display_name."""

    person_id: str
    display_name: str


class NestedSource(BaseModel):
    """Source model with nested dictionary fields."""

    subject: dict
    valueQuantity: dict


class NestedTarget(BaseModel):
    """Target model for nested source transformations."""

    patient_id: str
    value: float


class TransformSource(BaseModel):
    """Source model for transformation testing."""

    name: str
    reference: str


class TransformTarget(BaseModel):
    """Target model with transformed fields."""

    name_upper: str
    id: int


class ErrorTestSource(BaseModel):
    """Source model for error handling tests."""

    data: dict


class ErrorTestTarget(BaseModel):
    """Target model for error handling tests."""

    safe: Optional[str] = None
    error: Optional[str] = None


class NestedBidirectionalSource(BaseModel):
    """Model with nested structure for bidirectional tests."""

    patient: dict
    metadata: dict


class NestedBidirectionalTarget(BaseModel):
    """Target with different nesting for bidirectional tests."""

    id: str
    name: str
    extra_data: dict


# =============================================================================
# A/B Test Data Models (Complex to Flat transformation)
# =============================================================================


class NameData(BaseModel):
    """Nested name structure for A.json test data."""

    first: str
    given: list[str]
    prefix: Optional[str] = None
    suffix: Optional[str] = None


class AddressData(BaseModel):
    """Address structure for A.json test data."""

    street: list[str]
    city: str
    state: str
    postal_code: str
    country: str


class AddressHistory(BaseModel):
    """Address history for A.json test data."""

    current: AddressData
    previous: list[AddressData]


class ComplexPersonData(BaseModel):
    """Complex nested structure (A.json format)."""

    name: NameData
    address: AddressHistory


class FlatPersonData(BaseModel):
    """Flattened structure (B.json format)."""

    full_name: str
    current_address: str
    last_previous_address: str


# =============================================================================
# FHIR-style Models (Available for realistic test scenarios)
# =============================================================================


class FHIRObservation(BaseModel):
    """FHIR-style Observation for realistic transformations."""

    id: str
    subject: dict
    code: dict
    valueQuantity: Optional[dict] = None


class FlatObservation(BaseModel):
    """Flattened observation for analytics."""

    observation_id: str
    patient_id: str
    loinc_code: str
    value: Optional[float] = None
    unit: Optional[str] = None
