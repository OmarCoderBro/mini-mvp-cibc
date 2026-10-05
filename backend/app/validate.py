"""Deterministic Python checks over already-extracted, schema-valid fields.

This module has no knowledge of the LLM. It takes an `ExtractedFields`
value (already validated by Pydantic in schemas.py) and decides what, if
anything, is wrong with it. That separation is the point of the whole
design: the AI organizes information, this module is what actually
decides pass/fail, and both are testable independently of each other.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from .schemas import ExtractedFields, Issue

REQUIRED_FIELDS = (
    "legal_business_name",
    "registration_number",
    "registered_address",
    "issue_date",
    "expiration_date",
)

# Simple, readable format: letters/digits/hyphens, e.g. "BC-1029384".
REGISTRATION_NUMBER_PATTERN = r"^[A-Za-z0-9]+-[A-Za-z0-9]+$"

STATUS_READY = "ready_for_reviewer"
STATUS_NEEDS_ATTENTION = "needs_attention"


def _parse_date(value: str) -> date | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def run_checks(fields: ExtractedFields, *, today: date | None = None) -> list[Issue]:
    """Run all deterministic checks and return a list of specific issues.

    An empty list means every check passed. `today` is injectable so tests
    can pin "now" instead of depending on the wall clock.
    """
    today = today or date.today()
    issues: list[Issue] = []
    values = fields.model_dump()

    # 1. Required fields must be present and non-blank.
    for name in REQUIRED_FIELDS:
        raw = values.get(name)
        if raw is None or not str(raw).strip():
            issues.append(
                Issue(field=name, code="missing", message=f"{name} is missing.")
            )

    # 2. Format check: registration number, only if present.
    reg_number = values.get("registration_number")
    if reg_number and str(reg_number).strip():
        if not re.match(REGISTRATION_NUMBER_PATTERN, reg_number.strip()):
            issues.append(
                Issue(
                    field="registration_number",
                    code="malformed",
                    message=f"registration_number '{reg_number}' does not match the expected format (e.g. BC-1029384).",
                )
            )

    # 3. Date checks, only for dates that are present.
    issue_date = values.get("issue_date")
    expiration_date = values.get("expiration_date")

    parsed_issue = _parse_date(issue_date) if issue_date else None
    parsed_expiration = _parse_date(expiration_date) if expiration_date else None

    if issue_date and parsed_issue is None:
        issues.append(
            Issue(
                field="issue_date",
                code="malformed",
                message=f"issue_date '{issue_date}' is not a valid YYYY-MM-DD date.",
            )
        )

    if expiration_date and parsed_expiration is None:
        issues.append(
            Issue(
                field="expiration_date",
                code="malformed",
                message=f"expiration_date '{expiration_date}' is not a valid YYYY-MM-DD date.",
            )
        )

    if parsed_expiration is not None and parsed_expiration < today:
        issues.append(
            Issue(
                field="expiration_date",
                code="expired",
                message=f"Document expired on {parsed_expiration.isoformat()}.",
            )
        )

    if parsed_issue is not None and parsed_expiration is not None and parsed_issue > parsed_expiration:
        issues.append(
            Issue(
                field="issue_date",
                code="inconsistent_dates",
                message="issue_date is after expiration_date.",
            )
        )

    return issues


def compute_status(issues: list[Issue]) -> str:
    return STATUS_NEEDS_ATTENTION if issues else STATUS_READY


__all__ = [
    "run_checks",
    "compute_status",
    "STATUS_READY",
    "STATUS_NEEDS_ATTENTION",
    "REQUIRED_FIELDS",
]
