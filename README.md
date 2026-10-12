# Client Onboarding Document Review MVP - Omar Shatat

Synthetic onboarding document review using React → FastAPI → Claude (field extraction) → Python rules → PostgreSQL.

An LLM extracts five fields from a document, but deterministic Python rules, not the AI, decide whether it is "Ready for reviewer" or "Needs attention". A human reviewer makes the real decision.

Independent portfolio project, not affiliated with CIBC. All documents are fictional.

## Architecture

```
React page --> FastAPI --> Claude (extract 5 fields as JSON) --> Python rules --> PostgreSQL
```

- **FastAPI** (`POST /reviews`, `GET /reviews`, `GET /health`) runs extraction, validation, and saving.
- **Claude (Anthropic API)** pulls the business name, registration number, address, issue date, and expiration date from the text. Its output is checked against a strict schema before use.
- **Python rules** flag missing, malformed, expired, and inconsistent-date fields.
- **PostgreSQL** stores each review and powers the history table.
- **React + TypeScript (Vite)** is a single page: pick a sample document, review it, see results.

## Run locally

Requires Docker, Python 3.12, and Node.js. An Anthropic API key is needed only for real extraction; without one the app shows a clear error instead of a fake result.

**1. Start the database** (from the repo root)
```bash
docker compose up -d
```

**2. Start the API** (one terminal, from `backend/`)
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env        # then set ANTHROPIC_API_KEY in ../.env
uvicorn app.main:app --reload --port 8000
```

**3. Start the frontend** (second terminal, from `frontend/`)
```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (normally http://localhost:5173). Check the API at http://localhost:8000/health.

**Stop:** Ctrl+C both terminals, then `docker compose down`.

## Troubleshooting Tips for this MVP
- **If Port 8000 is still in use:**
`kill $(lsof -nP -tiTCP:8000 -sTCP:LISTEN)`.
- **To check if its running on there:**
`lsof -nP -iTCP:5173 -sTCP:LISTEN`.

- **Vite uses a different port (e.g. 5174):** restart the API with `FRONTEND_ORIGIN=http://localhost:5174 uvicorn app.main:app --reload --port 8000`.
- **Port 5433 already in use:** stop whatever holds it (the Uber Freight database also uses 5433), or change the port in `docker-compose.yml` and `DATABASE_URL`.
- **"Could not complete this review":** `ANTHROPIC_API_KEY` is missing or invalid in `.env`; fix it and restart the API.
