"""API-level tests for the single /reviews workflow.

The LLM is always mocked here (app.main.extract_fields is monkeypatched)
so these tests are repeatable and need no API key or network access.
The database layer is also faked so the suite does not require a running
PostgreSQL instance; backend/tests/test_db.py covers real persistence
against docker-compose Postgres separately.
"""
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app import main
from app.extract import ExtractionError
from app.schemas import ExtractedFields


class _FakeConn:
    def cursor(self):
        raise AssertionError("Fake connection should not be queried directly in these tests.")

    def commit(self):
        pass

    def close(self):
        pass


@pytest.fixture
def client(monkeypatch):
    # Prevent the real startup hook from trying to reach a real database.
    monkeypatch.setattr(main.db, "init_db", lambda *a, **k: None)

    @contextmanager
    def fake_get_connection():
        yield _FakeConn()

    monkeypatch.setattr(main.db, "get_connection", fake_get_connection)
    return TestClient(main.app)


def _fake_save_review(conn, *, document_name, extracted_fields, status, issues):
    return {
        "id": 1,
        "document_name": document_name,
        "extracted_fields": extracted_fields,
        "status": status,
        "issues": issues,
        "created_at": "2026-01-01T00:00:00+00:00",
    }


CLEAN_FIELDS = ExtractedFields(
    legal_business_name="Acme Widgets Holdings Ltd.",
    registration_number="BC-1029384",
    registered_address="100 Fictional Way, Toronto, ON",
    issue_date="2024-01-15",
    expiration_date="2027-01-15",
)


def test_health_reports_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_review_success_path(client, monkeypatch):
    monkeypatch.setattr(main, "extract_fields", lambda text: CLEAN_FIELDS)
    monkeypatch.setattr(main.db, "save_review", _fake_save_review)

    response = client.post(
        "/reviews",
        json={"document_name": "clean_registration.txt", "text": "some document text"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_reviewer"
    assert body["issues"] == []
    assert body["extracted_fields"]["legal_business_name"] == "Acme Widgets Holdings Ltd."


def test_create_review_with_issues_needs_attention(monkeypatch, client):
    expired_fields = ExtractedFields(
        legal_business_name="Northwind Traders Co.",
        registration_number="ON-5544332",
        registered_address="45 Imaginary Street, Ottawa, ON",
        issue_date="2019-04-02",
        expiration_date="2024-04-02",
    )
    monkeypatch.setattr(main, "extract_fields", lambda text: expired_fields)
    monkeypatch.setattr(main.db, "save_review", _fake_save_review)

    response = client.post(
        "/reviews",
        json={"document_name": "expired_registration.txt", "text": "some document text"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_attention"
    assert any(issue["code"] == "expired" for issue in body["issues"])


def test_create_review_rejects_invalid_llm_output_safely(monkeypatch, client):
    def boom(text):
        raise ExtractionError("Model response was not valid JSON")

    monkeypatch.setattr(main, "extract_fields", boom)
    save_called = False

    def spy_save_review(*args, **kwargs):
        nonlocal save_called
        save_called = True
        return _fake_save_review(*args, **kwargs)

    monkeypatch.setattr(main.db, "save_review", spy_save_review)

    response = client.post(
        "/reviews",
        json={"document_name": "broken.txt", "text": "some document text"},
    )

    assert response.status_code == 502
    assert "api_key" not in response.text.lower()
    assert "traceback" not in response.text.lower()
    assert save_called is False


def test_create_review_rejects_missing_document_name(client):
    response = client.post("/reviews", json={"text": "some document text"})
    assert response.status_code == 422


def test_create_review_rejects_empty_text(client):
    response = client.post("/reviews", json={"document_name": "a.txt", "text": ""})
    assert response.status_code == 422


def test_create_review_rejects_oversized_document(client):
    huge_text = "a" * (main.MAX_DOCUMENT_BYTES + 1)
    response = client.post(
        "/reviews",
        json={"document_name": "big.txt", "text": huge_text},
    )
    assert response.status_code == 413


def test_list_reviews_returns_history(monkeypatch, client):
    fake_rows = [
        {
            "id": 2,
            "document_name": "clean_registration.txt",
            "extracted_fields": CLEAN_FIELDS.model_dump(),
            "status": "ready_for_reviewer",
            "issues": [],
            "created_at": "2026-01-02T00:00:00+00:00",
        }
    ]
    monkeypatch.setattr(main.db, "list_reviews", lambda conn, limit=20: fake_rows)

    response = client.get("/reviews")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["document_name"] == "clean_registration.txt"
