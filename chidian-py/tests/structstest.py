"""
Strongly typed classes for testing.

Note: these are just used in the tests. And the `confest.py` returns weaker types intentionally
    These stronger classes are used for the `Piper` class
"""

from pydantic import BaseModel
from typing import Any


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
