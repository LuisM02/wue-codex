# WUE Codex Edition

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Modules 1 through 12 establish the backend foundation, persisted domain resources, five-view image workflow, replaceable classification boundary, canonical overall dimensions, editable parametric 2D plans, validated immutable design revisions, deterministic renderer-ready 3D geometry, an administrative material catalog, calculation-only material quantity and cost, and rule-based hardware quantity and cost estimation. The API includes typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, Alembic migrations, project/furniture CRUD, validated image storage, classification orchestration, Decimal unit conversion, deterministic geometry and costing services, and health endpoints.

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
- `POST /api/v1/plans/{plan_id}/finalize` — semantically validate and permanently finalize a draft
- `POST /api/v1/plans/{plan_id}/revisions` — deep-copy a finalized plan into the next editable revision
- `GET /api/v1/plans/{plan_id}/geometry-3d` — derive renderer-ready boxes from finalized geometry without persisting duplicates
- `GET /api/v1/plans/{plan_id}/material-quantity` — calculate per-component and total canonical volume without persisting results
- `GET /api/v1/plans/{plan_id}/material-cost?material_id={material_id}` — price finalized live volume with an active wood material
- `GET /api/v1/plans/{plan_id}/hardware-quantity` — apply the WUE v1 wood-screw connection rules without persisting results
- `GET /api/v1/plans/{plan_id}/hardware-cost?material_id={material_id}` — price the live wood-screw estimate using an eligible hardware catalog item

Generation creates the exact chair, dining-table, or bookshelf defaults documented by the WUE scope and locks overall dimensions in the same database transaction. Each overall axis must be at least 1 mm so proportional defaults remain representable at the stored precision; a failed generation leaves dimensions unlocked. A plan snapshots its furniture type, receives a positive revision number, and permits only one active draft for each furniture item. Component geometry is stored as `Decimal` millimeters. X/Y/Z are min-corner positions, rotation is expressed in degrees, quantity defaults to one, and sort order controls deterministic presentation. Draft components may temporarily omit depth and thickness; the later 3D stage will fail clearly if neither can supply extrusion depth.

Finalization enforces the approved semantics exactly: chairs require at least one leg plus exactly one seat panel and backrest panel; dining tables require at least one leg plus exactly one tabletop panel; bookshelves require one each of the five carcass panels and at least one uniquely named shelf matching `^shelf_[1-9]\d*$`. Unrecognized components prevent finalization. A finalized plan cannot be edited or directly unfinalized. Creating a revision deep-copies every geometry field into a new draft with new component identities, leaving the source unchanged. Initial-plan generation cannot be used to bypass this copy workflow after plan history exists.

3D reconstruction is calculation-only and accepts finalized plans exclusively. Each component becomes one box descriptor in millimeters: width remains X, height remains Y, and Z depth comes from component `depth` when present or `thickness` otherwise. Missing both fields produces a clear workflow error rather than fabricated geometry. Source X/Y/Z are retained as the minimum corner, while renderer center coordinates are calculated exactly as `(x + width/2, y + height/2, z + resolved_depth/2)` using `Decimal`. The response also identifies the chosen depth source and preserves scalar rotation, quantity, and sort order. Rotation is passed through in degrees; center calculation occurs before any renderer rotation. Quantity remains metadata because WUE has no rule for inventing offsets for repeated pieces.

Administrative material endpoints are:

- `POST/GET /api/v1/admin/materials`
- `GET/PATCH/DELETE /api/v1/admin/materials/{material_id}`
- `POST/GET /api/v1/admin/materials/{material_id}/prices`
- `GET/PATCH/DELETE /api/v1/admin/material-prices/{price_id}`

The catalog separates `wood` from `hardware`. Wood supports `mm3`, `cm3`, `m3`, and `board_ft`; hardware uses `piece`. Each dated price snapshots its material unit and contains no currency field. Type or unit changes are blocked after price history exists so old prices cannot silently change meaning. Price listing uses effective date descending, then creation time descending, and intentionally includes future dates. Material quantity remains independent of catalog selection and visual appearance: it multiplies each finalized box's width × height × resolved depth × quantity in cubic millimeters using `Decimal`, returns a transparent component breakdown, and stores no calculated result.

Material costing is also read-only. It requires an active `wood` material and selects the latest price by `effective_date DESC, created_at DESC` without filtering against today's date. Canonical volume conversion uses exact divisors: 1 cm3 = 1,000 mm3, 1 m3 = 1,000,000,000 mm3, and 1 board foot = 2,359,737.216 mm3. Calculations run with a fixed 40-significant-digit Decimal context and return per-component converted quantity, per-component cost, and totals. WUE does not attach currency semantics or hidden currency rounding, and visual appearance never selects or changes the costing material.

Hardware quantity estimation is calculation-only and does not require 3D depth. WUE v1 estimates `wood_screw` hardware at exactly two screws per connection: chairs count legs and the backrest, dining tables count legs, and bookshelves count side-to-top/bottom carcass connections plus shelf-to-side connections. Component `quantity` represents repeated physical pieces and contributes to these counts. Bookshelf back-panel fastening is deliberately excluded. These transparent rules are WUE estimation assumptions, not universal furniture standards.

Hardware costing derives that screw quantity live and multiplies it by the latest per-piece price using `Decimal`. The selected catalog item must be active, have type `hardware`, use unit `piece`, and have a normalized name exactly equal to `Wood screw`. Price selection uses `effective_date DESC, created_at DESC` and includes future dates. The response identifies the selected catalog item and price, preserves the connection breakdown, and applies no currency semantics or hidden rounding.

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
- Finalized 2D geometry is immutable and is the source of truth for deterministic 3D and calculations.
- Calculations use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
