"""PostgreSQL access using parameterized SQL only (no string-built queries).

Kept intentionally thin: one table, one insert, one select. psycopg
handles parameter binding so there is no SQL injection surface from
document_name or any extracted field.
"""
from __future__ import annotations

import json
import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://cibc_demo:cibc_demo@localhost:5433/cibc_demo",
)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS document_reviews (
    id SERIAL PRIMARY KEY,
    document_name TEXT NOT NULL,
    extracted_fields JSONB NOT NULL,
    status TEXT NOT NULL,
    issues JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

INSERT_REVIEW_SQL = """
INSERT INTO document_reviews (document_name, extracted_fields, status, issues)
VALUES (%s, %s, %s, %s)
RETURNING id, document_name, extracted_fields, status, issues, created_at;
"""

LIST_REVIEWS_SQL = """
SELECT id, document_name, extracted_fields, status, issues, created_at
FROM document_reviews
ORDER BY created_at DESC
LIMIT %s;
"""


@contextmanager
def get_connection() -> Generator[psycopg.Connection]:
    conn = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()


def init_db(conn: psycopg.Connection | None = None) -> None:
    """Create the table if it doesn't exist yet. Safe to call on every startup."""
    if conn is not None:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        return

    with get_connection() as owned_conn:
        with owned_conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        owned_conn.commit()


def save_review(
    conn: psycopg.Connection,
    *,
    document_name: str,
    extracted_fields: dict[str, Any],
    status: str,
    issues: list[dict[str, Any]],
) -> dict[str, Any]:
    with conn.cursor() as cur:
        cur.execute(
            INSERT_REVIEW_SQL,
            (document_name, json.dumps(extracted_fields), status, json.dumps(issues)),
        )
        row = cur.fetchone()
    conn.commit()
    return _row_to_review(row)


def list_reviews(conn: psycopg.Connection, limit: int = 20) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(LIST_REVIEWS_SQL, (limit,))
        rows = cur.fetchall()
    return [_row_to_review(row) for row in rows]


def _row_to_review(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "document_name": row["document_name"],
        "extracted_fields": row["extracted_fields"],
        "status": row["status"],
        "issues": row["issues"],
        "created_at": row["created_at"].isoformat(),
    }


__all__ = ["get_connection", "init_db", "save_review", "list_reviews", "DATABASE_URL"]