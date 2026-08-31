# WUE Codex Edition

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Modules 1 and 2 establish the backend foundation and the first persisted domain resources. The API includes typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, Alembic migrations, health endpoints, and project/furniture CRUD.

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

Apply deliberate schema migrations from `backend`:

```powershell
alembic upgrade head
```

Run the API:

```powershell
Set-Location backend
uvicorn app.main:app --reload
```

The initial endpoints are:

- `GET /api/v1/health` — confirms the API process is healthy without touching the database.
- `GET /api/v1/health/database` — executes `SELECT 1` and returns HTTP 503 with a plain-string detail when PostgreSQL is unavailable.
- `GET /docs` — interactive OpenAPI documentation.

Project and furniture endpoints are:

- `POST/GET /api/v1/projects`
- `GET/PATCH/DELETE /api/v1/projects/{project_id}`
- `POST/GET /api/v1/projects/{project_id}/furniture`
- `GET/PATCH/DELETE /api/v1/furniture/{furniture_id}`

Deleting a project cascades to its furniture. Furniture types are restricted in both API validation and PostgreSQL to `chair`, `dining_table`, and `bookshelf`.

## Tests

Run the fast suite from `backend`:

```powershell
pytest -m "not integration"
```

Database/API integration tests run Alembic against a real PostgreSQL database and are skipped unless `WUE_TEST_DATABASE_URL` is set. Each test uses an outer rollback transaction, so test records do not persist. After creating a dedicated test database, run the complete suite:

```powershell
$env:WUE_TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/wue_codex_test_db"
pytest
```

The test database must be dedicated to WUE tests. Migration state and ORM metadata are checked for drift on every complete run.

## Geometry and costing guardrails

- Canonical axes are X = left/right, Y = vertical, and Z = front/back; the floor is Y = 0.
- Overall dimensions use width = X, height = Y, and depth = Z.
- Finalized 2D geometry will be immutable and will be the source of truth for deterministic 3D and calculations.
- Calculations will use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
