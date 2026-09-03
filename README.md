# WUE Codex Edition

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Modules 1 through 17 plus the photo-reconstruction contract, runnable local vision baseline, and parametric CAD-like 2D editor establish the backend foundation, persisted domain resources, photo-first five-view workflow, replaceable AI boundaries, canonical overall dimensions, photo-derived part proposals, orthographic component editing, validated immutable design revisions, renderer-ready 3D geometry, separate administrative material and labor-rate catalogs, calculation-only cost domains, immutable quotation snapshots, and the guided web interface. The API includes typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, Alembic migrations, project/furniture CRUD, validated image storage, reconstruction provenance, deterministic calculations, and health endpoints.

## Repository layout

```text
backend/                    FastAPI backend and tests
frontend/                   React, TypeScript, Vite, Three.js, and Vitest app
reconstruction-worker/      Isolated five-view recognition/reconstruction service
IMPLEMENTATION_ROADMAP.md   Incremental backend/frontend delivery plan
```

## Requirements

- Python 3.12 or newer
- PostgreSQL
- Node.js 20.19 or newer

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

To use automatic recognition and the SAM 2.1 photo segmentation path, first run the isolated worker in another PowerShell window:

```powershell
.\scripts\start-sam2-worker.ps1
```

Then set `WUE_CLASSIFICATION_PROVIDER=http` and `WUE_RECONSTRUCTION_PROVIDER=http` before starting the API. Both service URLs default to `http://127.0.0.1:8010`. Leave either provider as `unconfigured` when an unavailable worker should produce an explicit 503 instead of a fallback result.

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

Each furniture item accepts at most one image per required view. JPEG, PNG, and WebP are verified from actual bytes rather than trusting filenames or MIME declarations. Deleting a project or furniture item also removes its stored image objects. Furniture starts with no assigned type; a successful classifier result or an explicit testing correction may assign only `chair`, `dining_table`, or `bookshelf`.

Classification endpoints are:

- `POST /api/v1/furniture/{furniture_id}/classification` — classify the complete five-view set and persist the latest result
- `GET /api/v1/furniture/{furniture_id}/classification` — retrieve the latest result

Classification requires all five views and verifies each stored object's SHA-256 integrity before invoking an adapter. The adapter can return only chair, dining table, or bookshelf. A successful prediction updates the furniture type; deleting a source image clears the derived type, while an explicit type correction invalidates both the stored classifier result and any derived geometry. The default adapter deliberately returns HTTP 503 because no provider is configured—it never fabricates a label. Set `WUE_CLASSIFICATION_PROVIDER=http` to use the isolated local worker.

Photo reconstruction endpoints are:

- `POST /api/v1/furniture/{furniture_id}/reconstruction` — send the exact five verified images, recognized type, and canonical scale to the configured AI adapter
- `GET /api/v1/furniture/{furniture_id}/reconstruction` — read the latest model/version, input signature, warnings, confidence, and detected parts

Each part records which source views support it, confidence, dimensions, 3-axis pose, and either a bounded box or an editable front-facing polygon profile. Changing an image, recognized type, or unlocked dimension set invalidates the proposal. The default reconstruction adapter returns HTTP 503 with an explicit message that WUE will not generate a generic substitute. Set `WUE_RECONSTRUCTION_PROVIDER=http` to use the isolated local service at `WUE_RECONSTRUCTION_SERVICE_URL`; the service receives five multipart image fields plus scale and checksum metadata. Large model dependencies and checkpoints do not run inside the business API.

The worker under `reconstruction-worker/` supports the dependency-light photo-derived baseline and a verified SAM 2.1 Base Plus segmentation path on the RTX 4070 through WSL. It checks that all five files are distinct, compares opposite views, rejects obvious orientation errors, records the loaded checkpoint hash, traces visible part silhouettes, and uses a side view for depth. Dense neural multi-view geometry and trained furniture-part recognition are still separate later stages, so hidden geometry remains visibly provisional. Start it on port 8010, then set both classification and reconstruction providers to `http`.

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
- `GET /api/v1/plans/{plan_id}/labor-quantity` — apply the WUE v1 labor-hour rules to finalized component semantics
- `GET /api/v1/plans/{plan_id}/labor-cost?labor_rate_id={labor_rate_id}` — price the live labor-hour estimate using an active labor rate
- `GET /api/v1/plans/{plan_id}/complete-cost?material_id={material_id}&hardware_material_id={hardware_material_id}&labor_rate_id={labor_rate_id}` — combine the three live cost domains
- `POST/GET /api/v1/plans/{plan_id}/quotations` — create and list immutable quotation snapshots
- `GET/DELETE /api/v1/quotations/{quotation_id}` — retrieve or remove one quotation snapshot

Generation is blocked until the furniture has a recognized or explicitly corrected type, dimensions, and a valid photo-derived reconstruction. The production path never invokes the old type-based default generator. A plan snapshots its source reconstruction and copies its detected parts so later AI reruns cannot silently rewrite a saved revision. Each overall axis must be at least 1 mm; a failed generation leaves dimensions unlocked. Component geometry is stored as `Decimal` millimeters. X/Y/Z are min-corner positions, rotation is stored on all three axes, quantity defaults to one, and sort order controls deterministic presentation.

The plan screen is a desktop-first, three-panel furniture CAD workspace. Front, Side, and Top views project the same canonical X/Y/Z geometry without mutating it. Draft components can be selected, dragged, resized with handles, edited numerically, added under furniture-specific rules, deleted with confirmation, snapped to a grid or nearby edges, and restored with bounded Undo/Redo history. Changes remain local during pointer movement and are persisted when the gesture ends; failed writes reload authoritative backend state. Traced polygons retain their photo-derived outlines, the optional front-photo overlay supports visual checking, and selected-part dimensions stay visible in the drawing. Finalized revisions remain inspectable and navigable but show a locked state and disable every geometry mutation.

Finalization retains the minimum structural checks—chair seat/backrest/legs, dining-table top/legs, and bookshelf carcass/shelves—but allows additional detected pieces such as arms, aprons, stretchers, slats, or trim. A finalized plan cannot be edited or directly unfinalized. Creating a revision deep-copies every geometry and provenance field into a new draft with new component identities, leaving the source unchanged.

3D reconstruction is calculation-only and accepts finalized plans exclusively. Bounded components remain boxes; traced profiles are extruded from their approved 2D polygon through the detected depth. Missing depth produces a clear workflow error rather than fabricated geometry. The response preserves the source outline, full rotation, quantity, and ordering. Material volume uses polygon area × depth for a traced part rather than its bounding rectangle.

Administrative material endpoints are:

- `POST/GET /api/v1/admin/materials`
- `GET/PATCH/DELETE /api/v1/admin/materials/{material_id}`
- `POST/GET /api/v1/admin/materials/{material_id}/prices`
- `GET/PATCH/DELETE /api/v1/admin/material-prices/{price_id}`

Administrative labor-rate endpoints are:

- `POST/GET /api/v1/admin/labor-rates`
- `GET/PATCH/DELETE /api/v1/admin/labor-rates/{labor_rate_id}`
- `POST/GET /api/v1/admin/labor-rates/{labor_rate_id}/prices`
- `GET/PATCH/DELETE /api/v1/admin/labor-rate-prices/{price_id}`

The catalog separates `wood` from `hardware`. Wood supports `mm3`, `cm3`, `m3`, and `board_ft`; hardware uses `piece`. Each dated price snapshots its material unit and contains no currency field. Type or unit changes are blocked after price history exists so old prices cannot silently change meaning. Price listing uses effective date descending, then creation time descending, and intentionally includes future dates. Material quantity remains independent of catalog selection and visual appearance: it multiplies each finalized box's width × height × resolved depth × quantity in cubic millimeters using `Decimal`, returns a transparent component breakdown, and stores no calculated result.

Material costing is also read-only. It requires an active `wood` material and selects the latest price by `effective_date DESC, created_at DESC` without filtering against today's date. Canonical volume conversion uses exact divisors: 1 cm3 = 1,000 mm3, 1 m3 = 1,000,000,000 mm3, and 1 board foot = 2,359,737.216 mm3. Calculations run with a fixed 40-significant-digit Decimal context and return per-component converted quantity, per-component cost, and totals. WUE does not attach currency semantics or hidden currency rounding, and visual appearance never selects or changes the costing material.

Hardware quantity estimation is calculation-only and does not require 3D depth. WUE v1 estimates `wood_screw` hardware at exactly two screws per connection: chairs count legs and the backrest, dining tables count legs, and bookshelves count side-to-top/bottom carcass connections plus shelf-to-side connections. Component `quantity` represents repeated physical pieces and contributes to these counts. Bookshelf back-panel fastening is deliberately excluded. These transparent rules are WUE estimation assumptions, not universal furniture standards.

Hardware costing derives that screw quantity live and multiplies it by the latest per-piece price using `Decimal`. The selected catalog item must be active, have type `hardware`, use unit `piece`, and have a normalized name exactly equal to `Wood screw`. Price selection uses `effective_date DESC, created_at DESC` and includes future dates. The response identifies the selected catalog item and price, preserves the connection breakdown, and applies no currency semantics or hidden rounding.

Labor-hour estimation is a separate calculation-only domain and does not use materials, prices, 3D geometry, or AI inference. The explicit WUE v1 assumptions are: chair base assembly 1.00 hour, 0.25 hour per leg, and 0.50 hour per backrest; dining-table base assembly 1.50 hours, 0.30 hour per leg, and 0.50 hour per tabletop; bookshelf base assembly 1.50 hours, 0.25 hour per recognized carcass panel, and 0.20 hour per valid shelf. Default totals are 2.50 hours, 3.20 hours, and 3.35 hours respectively. These are thesis estimation assumptions rather than universal industry standards.

Labor rates remain completely separate from materials. Each named rate has an active status and dated per-hour price history. Latest selection uses `effective_date DESC, created_at DESC`, deliberately includes future dates, and has no currency field. Labor costing is read-only: it multiplies the live finalized-plan labor hours by the latest selected hourly rate using a fixed high-precision `Decimal` context, preserves the rule breakdown, and applies no hidden rounding.

Complete cost estimation adds exactly wood/material cost, wood-screw hardware cost, and labor cost using `Decimal`. It contains no overhead term. Quotation creation accepts only the three selected catalog identifiers; clients cannot submit or override calculated totals. Each quotation snapshots the finalized plan revision, selected names and price identities, effective dates, quantities, rates, component costs, and exact total. Later catalog price changes affect new quotations but never rewrite existing ones. Quotation snapshots have no currency or overhead field and are immutable through the API.

## Tests

Run the fast suite from `backend`:

```powershell
pytest -m "not integration"
```

Database/API integration tests run Alembic against a real PostgreSQL database and are skipped unless `WUE_TEST_DATABASE_URL` is set. The configured PostgreSQL user must be allowed to create databases. The test session creates a uniquely named disposable sibling database, runs every migration and test there, and drops only that temporary database afterward. Per-test outer rollback transactions provide a second layer of isolation. Run the complete suite with:

```powershell
$env:WUE_TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/wue_codex_test_db"
pytest
```

The database named in `WUE_TEST_DATABASE_URL` is used only as a safe naming and connection base; its existing rows are not read or deleted. Migration state and ORM metadata are checked for drift inside the disposable database on every complete run.

`contracts/frontend-api.json` is the shared route contract for the web application. A frontend test invokes every API-client operation and compares the resulting methods and canonical paths with that manifest; a backend test compares the same manifest with FastAPI OpenAPI. A route used by one side but missing from the other therefore fails regression testing before deployment.

## Frontend setup

Install and run the web interface in a second terminal after starting the API:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite development server proxies `/api` to the backend at `http://localhost:8000`, so no browser CORS configuration is required. The interface guides users through an unclassified furniture record, five required views, recognition, dimensions, live part-by-part plan review and finalization, deterministic 3D inspection, separate appearance selection, exact costing, and immutable quotation snapshots.

Run frontend verification from `frontend`:

```powershell
npm test
npm run build
npm audit --audit-level=moderate
```

The Three.js viewer is loaded only when the preview step opens, keeping it out of the initial application bundle.

## Geometry and costing guardrails

- Canonical axes are X = left/right, Y = vertical, and Z = front/back; the floor is Y = 0.
- Overall dimensions use width = X, height = Y, and depth = Z.
- Finalized 2D geometry is immutable and is the source of truth for deterministic 3D and calculations.
- Calculations use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
