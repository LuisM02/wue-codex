# WUE Codex Edition

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Module 1 establishes the backend foundation. It includes a FastAPI application, typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, service and database health endpoints, and an initial pytest suite.

## Repository layout

```text
backend/                    FastAPI backend and tests
IMPLEMENTATION_ROADMAP.md   Incremental backend/frontend delivery plan
```

The frontend will be introduced in a later module using React, TypeScript, Vite, Three.js, React Three Fiber, Drei, and Vitest.

## Requirements

- Python 3.12 or newer
- PostgreSQL

## Backend setup

From the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env` with the PostgreSQL credentials for your machine. The application never creates or drops databases.

Run the API:

```powershell
Set-Location backend
uvicorn app.main:app --reload
```

The initial endpoints are:

- `GET /api/v1/health` — confirms the API process is healthy without touching the database.
- `GET /api/v1/health/database` — executes `SELECT 1` and returns HTTP 503 with a plain-string detail when PostgreSQL is unavailable.
- `GET /docs` — interactive OpenAPI documentation.

## Tests

Run the fast suite from `backend`:

```powershell
pytest -m "not integration"
```

Database/API integration tests use a real PostgreSQL database and are skipped unless `WUE_TEST_DATABASE_URL` is set. After creating a dedicated test database, run the complete suite:

```powershell
$env:WUE_TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/wue_codex_test_db"
pytest
```

The integration test is read-only and only executes `SELECT 1`.

## Geometry and costing guardrails

- Canonical axes are X = left/right, Y = vertical, and Z = front/back; the floor is Y = 0.
- Overall dimensions use width = X, height = Y, and depth = Z.
- Finalized 2D geometry will be immutable and will be the source of truth for deterministic 3D and calculations.
- Calculations will use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
