"""Tests for the LLM-facing boundary in app/extract.py.

No real network calls are made. We exercise the pure JSON-parsing /
schema-gating logic directly, which is the part that matters for safety:
bad model output must never silently become trusted data.
"""
import pytest

from app.extract import ExtractionError, _parse_model_json
from app.schemas import ExtractedFields


def test_valid_json_parses_into_extracted_fields():
    raw = (
        '{"legal_business_name": "Acme Widgets Holdings Ltd.", '
        '"registration_number": "BC-1029384", '
        '"registered_address": "100 Fictional Way, Toronto, ON", '
        '"issue_date": "2024-01-15", '
        '"expiration_date": "2027-01-15"}'
    )
    fields = _parse_model_json(raw)
    assert isinstance(fields, ExtractedFields)
    assert fields.legal_business_name == "Acme Widgets Holdings Ltd."


def test_json_wrapped_in_markdown_fence_still_parses():
    # Real models sometimes add a ```json ... ``` fence despite being asked
    # not to. This must still parse instead of raising ExtractionError.
    raw = (
        '```json\n'
        '{"legal_business_name": "Acme Widgets Holdings Ltd.", '
        '"registration_number": "BC-1029384", '
        '"registered_address": "100 Fictional Way, Toronto, ON", '
        '"issue_date": "2024-01-15", '
        '"expiration_date": "2027-01-15"}\n'
        '```'
    )
    fields = _parse_model_json(raw)
    assert fields.registration_number == "BC-1029384"


def test_valid_json_with_nulls_parses():
    raw = '{"legal_business_name": "Acme", "registration_number": null, "registered_address": null, "issue_date": null, "expiration_date": null}'
    fields = _parse_model_json(raw)
    assert fields.registration_number is None


def test_malformed_json_raises_extraction_error():
    with pytest.raises(ExtractionError):
        _parse_model_json("this is not json at all")


def test_json_array_raises_extraction_error():
    with pytest.raises(ExtractionError):
        _parse_model_json("[1, 2, 3]")


def test_unexpected_extra_field_raises_extraction_error():
    # extra="forbid" on ExtractedFields means an unexpected key must be
    # rejected rather than silently ignored or passed through.
    raw = '{"legal_business_name": "Acme", "unexpected_field": "oops"}'
    with pytest.raises(ExtractionError):
        _parse_model_json(raw)


def test_missing_api_key_raises_extraction_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    from app.extract import extract_fields

    with pytest.raises(ExtractionError):
        extract_fields("some document text")
