"""Persistence tests against a real PostgreSQL instance.

These require `docker compose up` (see README.md) to have a local
Postgres available at DATABASE_URL. They are skipped automatically if no
database is reachable, so the rest of the suite (validation, extraction,
API) stays runnable with no external services.
"""
import psycopg
import pytest

from app import db


def _db_available() -> bool:
    try:
        with psycopg.connect(db.DATABASE_URL, connect_timeout=2):
            return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _db_available(), reason="PostgreSQL is not reachable at DATABASE_URL")


@pytest.fixture
def conn():
    db.init_db()
    with db.get_connection() as connection:
        yield connection


def test_save_review_persists_status_and_timestamp(conn):
    saved = db.save_review(
        conn,
        document_name="pytest_clean.txt",
        extracted_fields={
            "legal_business_name": "Acme Widgets Holdings Ltd.",
            "registration_number": "BC-1029384",
            "registered_address": "100 Fictional Way, Toronto, ON",
            "issue_date": "2024-01-15",
            "expiration_date": "2027-01-15",
        },
        status="ready_for_reviewer",
        issues=[],
    )

    assert saved["id"] is not None
    assert saved["status"] == "ready_for_reviewer"
    assert saved["created_at"] is not None
    assert saved["document_name"] == "pytest_clean.txt"


def test_list_reviews_returns_most_recent_first(conn):
    db.save_review(
        conn,
        document_name="pytest_first.txt",
        extracted_fields={"legal_business_name": "First"},
        status="needs_attention",
        issues=[{"field": "registration_number", "code": "missing", "message": "missing"}],
    )
    db.save_review(
        conn,
        document_name="pytest_second.txt",
        extracted_fields={"legal_business_name": "Second"},
        status="ready_for_reviewer",
        issues=[],
    )

    rows = db.list_reviews(conn, limit=2)
    assert len(rows) >= 2
    assert rows[0]["document_name"] == "pytest_second.txt"
