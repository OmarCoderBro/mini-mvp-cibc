# CIBC Client Onboarding Document Review — Demo

**This is an independent portfolio project.** It is inspired by a public CIBC Software Engineer
Apprentice job posting but is **not affiliated with, endorsed by, or built using any real CIBC
system, data, or codebase**. It is a **local-only demo** and is **not** a compliance, legal, or
identity-verification system. All documents and values are fictional.

## What this demonstrates

A reviewer selects a synthetic business-registration text document, an LLM extracts five fields
into structured JSON, and deterministic Python rules decide whether the document is **Ready for
reviewer** or **Needs attention**. The AI never makes the pass/fail decision and never represents
a result as final onboarding approval — Python rules decide what's wrong, and a human reviewer is
responsible for the actual decision.

## Architecture

```
frontend/  React + TypeScript + Vite, one page, no auth, no routing
backend/app/
  main.py      FastAPI routes (GET /health, POST /reviews, GET /reviews)
  schemas.py   Pydantic schemas — the strict gate between LLM output and the app
  extract.py   The only module that calls the LLM
  validate.py  Pure, LLM-free deterministic checks (missing/malformed/expired)
  db.py        Parameterized SQL against PostgreSQL
backend/sample_documents/   Synthetic plain-text example documents
backend/tests/              pytest suite (LLM always mocked)
docker-compose.yml          Local PostgreSQL only
```

## Prerequisites

- Python 3.12 (3.14 currently lacks prebuilt wheels for some pinned deps — see Troubleshooting)
- Node.js 20+ and npm
- Docker Desktop (for local PostgreSQL)
- An Anthropic API key, **only if you want real LLM extraction**. Without one, the app still runs
  end-to-end and correctly returns a clear error instead of a fake successful review.

## 1. Start PostgreSQL

```bash
docker compose up -d
```

This starts Postgres on **localhost:5433** (not 5432, to avoid clashing with any Postgres already
running on your machine) with user/password/db all set to `cibc_demo`.

## 2. Backend setup

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp ../.env.example ../.env       # project-root .env, read by the backend
# edit ../.env and set ANTHROPIC_API_KEY if you want real extraction
```

Run the backend from the `backend/` directory so environment variables load correctly, or export
them in your shell. The variables used are:

| Variable | Purpose | Default |
|---|---|---|
| `ANTHROPIC_API_KEY` | Backend-only LLM credential. Never sent to the frontend. | *(required for real extraction)* |
| `ANTHROPIC_MODEL` | Model used for the one extraction call. | `claude-sonnet-5` |
| `DATABASE_URL` | Postgres connection string. | `postgresql://cibc_demo:cibc_demo@localhost:5433/cibc_demo` |
| `FRONTEND_ORIGIN` | Allowed CORS origin. | `http://localhost:5173` |

Start the API (it loads `../.env` automatically on startup via `python-dotenv`):

```bash
uvicorn app.main:app --reload --port 8000
```

Check it's up:

```bash
curl http://localhost:8000/health
# {"status":"ok","database":"ok"}
```

## 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env.local   # optional; default already points at localhost:8000
npm run dev
```

Open the URL Vite prints (typically `http://localhost:5173`).

## 4. Try the demo

1. Pick one of the three sample documents (clean / expired / missing fields).
2. Click **Review document**.
3. Watch the loading state, then see extracted fields, passed/failed checks, and a status banner.
4. The review appears in the history table below.

**Without an `ANTHROPIC_API_KEY` configured**, step 2 will correctly show an error state
("Could not complete this review") instead of saving a misleading result — this is intended
behavior, not a bug. Add a real key to `.env` and restart the backend to see live extraction.

## Running tests

```bash
cd backend
source .venv/bin/activate
python -m pytest -v
```

The LLM is mocked in every test (`app.extract.extract_fields` or the lower-level JSON parser is
monkeypatched) — no API key or network access is required. Tests in `tests/test_db.py` exercise
real persistence against PostgreSQL and are automatically **skipped** if `docker compose up` isn't
running; everything else runs with no external services.

Last verified run: **24 passed** (22 always-on + 2 DB integration tests, with Postgres up).

## Sample documents and expected outcomes

| File | Expected status | Why |
|---|---|---|
| `clean_registration.txt` | Ready for reviewer | All fields present, valid, not expired |
| `expired_registration.txt` | Needs attention | `expiration_date` is in the past |
| `missing_fields_registration.txt` | Needs attention | `registration_number` and `expiration_date` missing |

## Security and scope notes

- LLM credentials live only in backend environment variables; the frontend never sees them.
- `.env` is git-ignored; only `.env.example` (placeholder values) is committed.
- Document text is treated as **untrusted input, not instructions** — the extraction prompt
  explicitly tells the model to ignore any instruction-like content inside the document.
- Upload size is capped (20 KB) and rejected with a `413` beyond that.
- All SQL is parameterized (`psycopg` with `%s` placeholders) — no string-built queries.
- CORS is restricted to the configured local frontend origin.
- No stack traces, secrets, or raw document text are ever returned in error responses.
- Out of scope, by design: real CIBC systems, real identity/business verification, PDF/OCR,
  e-signatures, email, chatbots, authentication, cloud deployment, and automatic onboarding
  approval. See `CLAUDE.md` for the full boundary.

## Troubleshooting

- **Port 5432 already in use / wrong role error**: this machine likely has another Postgres
  running on 5432. This repo's `docker-compose.yml` already maps to **5433** to avoid that; make
  sure `DATABASE_URL` in your `.env` also uses `5433`.
- **`pip install` fails building `pydantic-core` / `psycopg[binary]` wheels**: this has been seen
  on very new Python releases (e.g. 3.14) that lack prebuilt wheels yet. Use Python 3.12 or 3.13
  for the backend virtualenv instead.
