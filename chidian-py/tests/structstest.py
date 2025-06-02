"""
Strongly typed classes for testing.

NOTE: these are just used in the tests. And the `confest.py` returns weaker types intentionally
    These stronger classes are used for the `Piper` class
"""

from typing import Any

from pydantic import BaseModel

# TODO: This would be a good place to define an area of shared structs used across test files ()
#       ... maybe this could be some OMOP<>FHIR mappings... I guess why not? Makes it easier to reason about too with concrete example

# TODO: Add `A` and `B` classes... can be centering example


class SimpleMessage(BaseModel):
    msg: str


class InnerNestedDict(BaseModel):
    num: int
    text: str
    inner: SimpleMessage


class PatientData(BaseModel):
    id: str
    active: bool


class DetailedPatientData(PatientData):
    ints: list[int]
    some_dict: dict[str, Any]
    list_of_dicts: list[InnerNestedDict]


class SimpleData(BaseModel):
    data: dict[str, Any]
    list_data: list[dict[str, Any]]


class NestedData(BaseModel):
    data: list[PatientData]
