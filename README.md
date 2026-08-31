# WUE Codex Edition

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Modules 1 through 6 establish the backend foundation, persisted domain resources, five-view image workflow, replaceable classification boundary, canonical overall dimensions, and editable parametric 2D plans. The API includes typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, Alembic migrations, project/furniture CRUD, validated image storage, classification orchestration, Decimal unit conversion, deterministic default geometry, and health endpoints.

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

Image files default to `backend/uploads` when the API is run from `backend`. `WUE_UPLOAD_DIRECTORY`, `WUE_MAX_IMAGE_BYTES`, and `WUE_MAX_IMAGE_PIXELS` can change the storage root and safety limits. Image metadata is stored in PostgreSQL; encoded image bytes are stored behind a replaceable local-storage abstraction.

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

Five-view image endpoints are:

- `POST /api/v1/furniture/{furniture_id}/images/{view}` — multipart upload with optional `source=upload|camera_capture`
- `GET /api/v1/furniture/{furniture_id}/images` — metadata in front, back, left, right, top order
- `GET /api/v1/furniture/{furniture_id}/images/{view}` — metadata for one view
- `GET /api/v1/furniture/{furniture_id}/images/{view}/content` — validated encoded image bytes
- `DELETE /api/v1/furniture/{furniture_id}/images/{view}` — remove metadata and stored bytes

Each furniture item accepts at most one image per required view. JPEG, PNG, and WebP are verified from actual bytes rather than trusting filenames or MIME declarations. Deleting a project or furniture item also removes its stored image objects. Furniture types remain restricted in both API validation and PostgreSQL to `chair`, `dining_table`, and `bookshelf`.

Classification endpoints are:

- `POST /api/v1/furniture/{furniture_id}/classification` — classify the complete five-view set and persist the latest result
- `GET /api/v1/furniture/{furniture_id}/classification` — retrieve the latest result

Classification requires all five views and verifies each stored object's SHA-256 integrity before invoking an adapter. The adapter can return only chair, dining table, or bookshelf. A successful prediction updates the furniture type; deleting a source image or manually changing that type invalidates the stored result. The default adapter deliberately returns HTTP 503 because no real AI model is configured yet—it never fabricates a label from filenames or unrelated business state.

Overall dimension endpoints are:

- `PUT /api/v1/furniture/{furniture_id}/dimensions` — create or replace the complete width, height, and depth set while unlocked
- `GET /api/v1/furniture/{furniture_id}/dimensions` — retrieve canonical millimeter values and provenance
- `DELETE /api/v1/furniture/{furniture_id}/dimensions` — remove an unlocked set

Dimension input accepts `mm`, `cm`, `m`, and `in`; conversion uses backend `Decimal` values and stores width=X, height=Y, and depth=Z in millimeters. Manual input is the default trusted source and cannot be overwritten by an AI estimate. The first 2D-plan generation calls the dimension lock in the same transaction. There is no unlock operation.

Parametric 2D plan endpoints are:

- `POST /api/v1/furniture/{furniture_id}/plans` — generate the first editable draft from canonical dimensions
- `GET /api/v1/furniture/{furniture_id}/plans` — list revision-ready plans and their ordered components
- `GET /api/v1/plans/{plan_id}` — retrieve one plan with its ordered components
- `POST /api/v1/plans/{plan_id}/components` — add a supported panel or leg to a draft
- `PATCH /api/v1/plans/{plan_id}/components/{component_id}` — edit draft geometry
- `DELETE /api/v1/plans/{plan_id}/components/{component_id}` — remove a draft component

Generation creates the exact chair, dining-table, or bookshelf defaults documented by the WUE scope and locks overall dimensions in the same database transaction. Each overall axis must be at least 1 mm so proportional defaults remain representable at the stored precision; a failed generation leaves dimensions unlocked. A plan snapshots its furniture type, receives a positive revision number, and permits only one active draft for each furniture item. Component geometry is stored as `Decimal` millimeters. X/Y/Z are min-corner positions, rotation is expressed in degrees, quantity defaults to one, and sort order controls deterministic presentation. Draft components may temporarily omit depth and thickness; the later 3D stage will fail clearly if neither can supply extrusion depth. Finalization is intentionally reserved for Module 7, while the persistence and service layers already reject component mutations when a plan is finalized.

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
- Finalized 2D geometry is guarded as immutable and will be the source of truth for deterministic 3D and calculations after Module 7 exposes validated finalization.
- Calculations will use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
