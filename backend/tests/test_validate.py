"""Tests for the deterministic Python checks in app/validate.py.

These tests never touch the LLM -- they construct ExtractedFields
directly, which is the point of keeping extraction and validation
separate.
"""
from datetime import date

from app.schemas import ExtractedFields
from app.validate import STATUS_NEEDS_ATTENTION, STATUS_READY, compute_status, run_checks


def make_fields(**overrides) -> ExtractedFields:
    base = dict(
        legal_business_name="Acme Widgets Holdings Ltd.",
        registration_number="BC-1029384",
        registered_address="100 Fictional Way, Toronto, ON",
        issue_date="2024-01-15",
        expiration_date="2027-01-15",
    )
    base.update(overrides)
    return ExtractedFields(**base)


FIXED_TODAY = date(2026, 1, 1)


def test_clean_document_passes_with_no_issues():
    fields = make_fields()
    issues = run_checks(fields, today=FIXED_TODAY)
    assert issues == []
    assert compute_status(issues) == STATUS_READY


def test_missing_required_field_is_reported():
    fields = make_fields(registration_number=None)
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("registration_number", "missing") in codes
    assert compute_status(issues) == STATUS_NEEDS_ATTENTION


def test_blank_required_field_is_treated_as_missing():
    fields = make_fields(legal_business_name="   ")
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("legal_business_name", "missing") in codes


def test_malformed_registration_number_is_reported():
    fields = make_fields(registration_number="not-a-valid-number!!")
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("registration_number", "malformed") in codes
    assert compute_status(issues) == STATUS_NEEDS_ATTENTION


def test_malformed_date_is_reported():
    fields = make_fields(expiration_date="not-a-date")
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("expiration_date", "malformed") in codes


def test_expired_document_needs_attention():
    fields = make_fields(issue_date="2019-04-02", expiration_date="2024-04-02")
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("expiration_date", "expired") in codes
    assert compute_status(issues) == STATUS_NEEDS_ATTENTION


def test_issue_date_after_expiration_is_inconsistent():
    fields = make_fields(issue_date="2027-01-15", expiration_date="2024-01-15")
    issues = run_checks(fields, today=FIXED_TODAY)
    codes = [(i.field, i.code) for i in issues]
    assert ("issue_date", "inconsistent_dates") in codes


def test_multiple_issues_all_reported_together():
    fields = make_fields(registration_number=None, expiration_date="2024-04-02")
    issues = run_checks(fields, today=FIXED_TODAY)
    assert len(issues) >= 2
    assert compute_status(issues) == STATUS_NEEDS_ATTENTION
