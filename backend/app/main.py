"""FastAPI app: three endpoints, one vertical slice.

GET  /health   - liveness + DB reachability
POST /reviews  - extract -> validate -> persist -> return
GET  /reviews  - recent review history
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load the project-root .env (backend/app/main.py -> backend/ -> project root)
# before any module below reads os.environ at import time (db.py and
# extract.py both read config lazily or at import time).
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from . import db
from .extract import ExtractionError, extract_fields
from .schemas import ReviewRequest, ReviewResult
from .validate import compute_status, run_checks

logger = logging.getLogger("cibc_demo")

MAX_DOCUMENT_BYTES = 20_000  # ~20 KB is generous for a synthetic plain-text demo doc


@asynccontextmanager
async def _lifespan(app: FastAPI):
    try:
        db.init_db()
    except Exception:
        # Don't crash app startup/tests that don't need the DB; /health will
        # report the DB as unreachable instead.
        logger.warning("Database initialization failed at startup.", exc_info=True)
    yield


app = FastAPI(title="CIBC Onboarding Document Review MVP (demo)", lifespan=_lifespan)

_frontend_origin = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_frontend_origin],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    db_ok = True
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
    except Exception:
        db_ok = False
    return {"status": "ok", "database": "ok" if db_ok else "unreachable"}


@app.post("/reviews", response_model=ReviewResult)
def create_review(payload: ReviewRequest) -> ReviewResult:
    document_bytes = payload.text.encode("utf-8")
    if len(document_bytes) > MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Document text exceeds the {MAX_DOCUMENT_BYTES} byte limit for this demo.",
        )

    try:
        fields = extract_fields(payload.text)
    except ExtractionError as exc:
        logger.warning("Extraction failed for document_name=%s: %s", payload.document_name, exc)
        raise HTTPException(status_code=502, detail="Could not extract fields from the document.") from exc

    issues = run_checks(fields)
    status = compute_status(issues)

    try:
        with db.get_connection() as conn:
            saved = db.save_review(
                conn,
                document_name=payload.document_name,
                extracted_fields=fields.model_dump(),
                status=status,
                issues=[issue.model_dump() for issue in issues],
            )
    except Exception as exc:
        logger.error("Failed to persist review for document_name=%s", payload.document_name, exc_info=True)
        raise HTTPException(status_code=500, detail="Could not save the review.") from exc

    return ReviewResult(**saved)


@app.get("/reviews", response_model=list[ReviewResult])
def list_reviews(limit: int = 20) -> list[ReviewResult]:
    capped_limit = max(1, min(limit, 100))
    try:
        with db.get_connection() as conn:
            rows = db.list_reviews(conn, limit=capped_limit)
    except Exception as exc:
        logger.error("Failed to list reviews", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load review history.") from exc

    return [ReviewResult(**row) for row in rows]


__all__ = ["app"]
