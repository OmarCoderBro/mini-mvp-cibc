"""Pydantic schemas for the document review MVP.

`ExtractedFields` is the strict gate between untrusted LLM output and the
rest of the application. Nothing downstream (validation, persistence, API
responses) ever sees raw model output -- only a value that has already
passed this schema.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ExtractedFields(BaseModel):
    """The fixed set of fields the LLM is asked to extract.

    All fields are optional strings at the schema level because a
    document may legitimately omit a value (e.g. a missing expiration
    date) -- that absence is something the deterministic Python rules
    should flag as an issue, not something that should make the whole
    extraction fail. Date-shaped fields are validated for format by the
    rules in validate.py, not here, so that a malformed date becomes a
    reported issue instead of a hard extraction error.
    """

    model_config = ConfigDict(extra="forbid")

    legal_business_name: Optional[str] = Field(default=None)
    registration_number: Optional[str] = Field(default=None)
    registered_address: Optional[str] = Field(default=None)
    issue_date: Optional[str] = Field(default=None)
    expiration_date: Optional[str] = Field(default=None)


class Issue(BaseModel):
    """A single, specific reason a document needs attention."""

    field: str
    code: str
    message: str


class ReviewRequest(BaseModel):
    """Incoming request body for POST /reviews."""

    model_config = ConfigDict(extra="forbid")

    document_name: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)


class ReviewResult(BaseModel):
    """Response body for a completed review, and the shape persisted to DB."""

    id: int
    document_name: str
    status: str
    extracted_fields: ExtractedFields
    issues: list[Issue]
    created_at: str


__all__ = [
    "ExtractedFields",
    "Issue",
    "ReviewRequest",
    "ReviewResult",
]
