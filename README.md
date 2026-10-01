# WUE Furniture Workshop

Latest table-mapping revision (October 2, 2026): the worker now locates the
side elevation's own projected tabletop band instead of reusing the front
photo's height fraction. Side leg sampling and apron mapping use that boundary;
the independently traced apron height is retained rather than snapping an
existing part into place. Severe aspect-ratio mismatches still return HTTP422,
but the message now identifies a photo/dimension proportion mismatch instead
of claiming a confirmed wrong orientation. Thresholds and recognition gates
are unchanged. Worker/provider provenance is now **0.3.1**; saved records keep
their original provenance. **66 worker tests and 15 focused backend HTTP-adapter
tests pass.** A read-only live SAM probe of the existing table photos retained
nine proposed parts and reduced the new proposal's side-apron gap from about
17.62 mm to 0 mm. This is not physical accuracy validation. No saved plan was
replaced or finalized; two independently observed position edits in the audit
draft were preserved. Protected retained designs and the sample quote still
match their checkpoint. Frontend/full backend suites and the build were not
rerun for this worker-only change (last verified: 115 frontend, 381 backend,
build passing with the existing large viewer-chunk warning).
See [table mapping checkpoint](docs/TABLE_MAPPING_CHECKPOINT_2026-10-02.md).

Latest editor-cleanup revision (October 2, 2026): part-by-part navigation stays
visible, while detailed review instructions, sizes and photo-comparison buttons
are collapsed under **Review help & photo comparison**. The required review and
finalization gates remain unchanged. Traced vertices are hidden in normal move/
resize mode. **Edit outline** shows one larger active vertex at a time; click
near an outline corner or choose its point number, then drag the active dot.
Point insertion/removal is explicit and available only in outline-edit mode.
Changing the selected part, view or locked state exits that mode. No automatic
vertex reduction or changes to saved geometry, calibration, estimates or quotes
were made. **115 frontend tests pass in 14 files; production build passes.**
Backend/worker code is unchanged and their suites were not rerun. The existing
large viewer-chunk warning remains. Live checks exercised mode entry/exit,
Front/Back point selection and the collapsed help section without geometry
writes; protected saved designs and quotations were verified unchanged.

Preceding editor-view revision (October 2, 2026): the CAD toolbar and part-photo
comparison controls now expose **Front, Back, Left, Right, and Top** separately.
Each named view uses its matching photograph. Back and Left reverse the display
direction while movement, resizing and outline edits retain canonical X/Y/Z
geometry. Five-view navigation wraps onto its own toolbar row on narrow screens.
**110 frontend tests pass across 13 files; TypeScript/production build passes.**
Backend/worker code is unchanged (last verified totals: 381/62); those suites
were not rerun for this frontend-only change. The existing large viewer-chunk
warning remains. Live five-view inspection preserved the audit draft, retained
designs, photo calibration and sample quotation. This is inspection usability,
not new reconstruction accuracy or a correction of the known table apron gap.

Latest verified prototype checkpoint and remaining limits:
[October 1, 2026 checkpoint](docs/PROTOTYPE_CHECKPOINT_2026-10-01.md).

Latest recognition safety follow-on: unsupported/uncertain structural evidence
now returns422 instead of forcing the highest-scoring furniture label. Seat/
backrest/leg, tabletop/leg and shelf/frame evidence is required across relevant
views. The ordinary manual-type selector is removed; reconstruction requires
a saved recognition matching the current five-photo signature and requested
type, and the worker checks that type again. Existing saved designs remain
inspectable. **Backend381, frontend89 and worker62 tests pass; build passes.**
Actual saved chair/table/bookshelf photo probes pass without changing their
stored state. This is a conservative heuristic support gate, not trained
open-world recognition: furniture-like impostors can pass and unusual/occluded
valid furniture can be rejected. The displayed shape score is not accuracy.

Preceding chair pose follow-on: agreeing mirrored-left/right silhouette centerlines
can now estimate a conservative straight lean for detected backrest posts/slats.
Unstable, conflicting, excessive or out-of-bounds fits keep the original upright
proposal with an explicit warning. The supplied slatted chair yields about8.5°
in a **separate unreviewed approximate-size draft**; the top rail and rear legs
are not automatically tilted. This is a projected estimate, not a measured
physical angle or validated reconstruction accuracy. **Fresh backend379,
frontend85 and worker56 tests pass; production build passes.** Retained table,
chair, bookshelf and sample-price quotation remain preserved. Curvature,
overlapping stock depth and physical accuracy evaluation are still incomplete.

Preceding CAD review follow-on: photo-derived drawings have Previous/Next part
navigation, available Front/Back–Left/Right–Top photo comparison buttons, and
a display-only selected-part isolation toggle. Plain-language part checks and
model-size/confidence reminders support review without recording it for the
user. **85 frontend tests pass; production build passes.** Live bookshelf
inspection left every saved plan field and its null review timestamp unchanged.
This improves review usability, not automatic reconstruction accuracy.

Latest bookshelf terminal-face follow-on: the bottom panel now uses its own
coherent edge pair when visible, instead of always copying an interior shelf's
thickness. Missing cap/bottom boundaries are explicitly labeled provisional.
**46 worker tests pass**. A read-only SAM probe still finds nine parts in the
saved bookshelf; its ambiguous terminal estimates remain unchanged. This does
not establish physical accuracy or alter any saved draft/finalized drawing.

Latest failure-feedback follow-on: explicit worker photo rejections now return
HTTP422 through the business API, distinct from unavailable services (503) and
invalid worker responses (502). Recognition/reconstruction screens retain the
specific reason with correction or service-readiness guidance. Manual type
selection is explicitly not AI recognition and does not restore reconstruction.
**377 backend tests and 65 frontend tests pass; production build passes.**
Worker42 was the unchanged preceding result at that failure-feedback checkpoint.
Failed analysis tests verify saved recognition, analysis and geometry are retained.

October 1 bookshelf follow-on: solid-backed bookshelves now use sustained
internal grayscale edge pairs for shelf proposals instead of trying to infer
all shelves from the foreground silhouette. The saved bookshelf photos now
propose four shelves and nine parts; the previous six-part finalized test is
preserved. No guessed middle shelf is inserted when evidence is absent.
**42 worker tests pass**; panel depths, back/terminal thickness and physical
accuracy remain provisional. This is heuristic image analysis after segmentation,
not newly trained neural shelf recognition.

WUE (Wood U Estimate) is an AI-assisted system for reconstructing wooden furniture, estimating materials and labor, and producing quotations. This repository is a new, independent implementation and supports exactly three furniture types: `chair`, `dining_table`, and `bookshelf`.

Modules 1 through 17 plus the photo-reconstruction contract, runnable local vision baseline, parametric CAD-like 2D editor, and BOM-first costing workflow establish the backend foundation, persisted domain resources, photo-first five-view workflow, replaceable AI boundaries, canonical overall dimensions, photo-derived part proposals, orthographic component editing, validated immutable design revisions, renderer-ready 3D geometry, separate administrative material and labor-rate catalogs, calculation-only cost domains, immutable quotation snapshots, and the guided web interface. The API includes typed environment configuration, a synchronous SQLAlchemy 2.x/PostgreSQL session layer, Alembic migrations, project/furniture CRUD, validated image storage, reconstruction provenance, deterministic calculations, and health endpoints.

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
- `PUT /api/v1/furniture/{furniture_id}/images/{view}/calibration` — save the normalized furniture crop and horizontal mirror state used by the CAD overlay
- `DELETE /api/v1/furniture/{furniture_id}/images/{view}` — remove metadata and stored bytes

Each furniture item accepts at most one image per required view. JPEG, PNG, and WebP are verified from actual bytes rather than trusting filenames or MIME declarations. Each saved view also owns a bounded, normalized object crop (`object_left_ratio`, `object_top_ratio`, `object_width_ratio`, `object_height_ratio`) and `is_mirrored` flag. The CAD editor uses that calibration to map the visible furniture onto the measured Front, Side, or Top bounds; calibration is review metadata and deliberately does not invalidate the unchanged source image's AI outputs. Deleting a project or furniture item also removes its stored image objects. Furniture starts with no assigned type; a successful classifier result or an explicit testing correction may assign only `chair`, `dining_table`, or `bookshelf`.

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
- `POST /api/v1/plans/{plan_id}/review-parts` — record the user's review of an editable AI part proposal
- `POST /api/v1/plans/{plan_id}/finalize` — require part review, semantically validate, and permanently finalize a photo-derived draft
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

The plan screen is a desktop-first, three-panel furniture CAD workspace. Front, Back, Left, Right, and Top views project the same canonical X/Y/Z geometry without mutating it. Each named view selects only its matching reference photograph; opposite-view photographs are not silently substituted. Back and Left reverse the horizontal display direction, not the saved axes. The user may horizontally mirror or crop-calibrate the current reference to account for image orientation; these controls change only the visual overlay, never geometry or source images. A new photo-derived draft begins in explicit part-review mode with a matching photograph visible: the user compares the AI proposal, renames or resizes incorrect parts, adds omissions, removes false detections, and confirms that review before finalization becomes available. Draft components can be selected, dragged, resized with handles, edited numerically, added under furniture-specific rules, deleted with confirmation, snapped to a grid or nearby edges, and restored with bounded Undo/Redo history. In unrotated Front and Back views, every traced polygon exposes round control points that can be dragged over the reference photograph with optional 5 mm snapping; the user can insert a midpoint on a selected or longest edge and remove a selected point while retaining at least three vertices. Rotated parts use Properties for local size and angle changes rather than interpreting projected bounds as local dimensions. Frontend and backend validation reject repeated edges, zero-area profiles, and self-intersecting outlines. Changes remain local during pointer movement and are persisted when the gesture ends; failed writes reload authoritative backend state. The edited polygon remains the single outline used by 3D extrusion and polygon-area material quantity. Selected-part dimensions stay visible in the drawing. Finalized revisions remain inspectable and navigable but show a locked state and disable every geometry mutation.

Finalization first requires a persisted user review for every newly reconstructed photo-derived draft. It then retains the minimum structural checks—chair seat/backrest/legs, dining-table top/legs, and bookshelf carcass/shelves—but allows additional detected pieces such as arms, aprons, stretchers, slats, or trim. A finalized plan cannot be edited or directly unfinalized. Creating a revision deep-copies every geometry and provenance field into a new draft with new component identities, leaving the source unchanged; rebuilding from photos creates a fresh unreviewed proposal.

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

### Windows demo startup and recovery

From the repository root, run:

```powershell
.\scripts\start-wue.ps1
```

This local-only launcher uses the existing Python/Node dependencies and WSL SAM
installation. It starts missing services in hidden background processes, reuses
healthy services, and uses worker8010/API8011/frontend5174 explicitly. It checks
PostgreSQL health, the frontend API proxy, and the expected SAM 2.1 GPU provider.
It never installs packages, migrates/resets databases, stops conflicting apps,
or touches the unrelated app on port8000. If an occupied target port is unhealthy
or belongs to another service, it stops with an explanation instead of replacing
that process. Background logs are local under ignored `.wue-runtime/`.

For a read-only readiness check use `scripts/start-wue.ps1 -CheckOnly`. Test its
identification/port/hidden-process safeguards with
`scripts/test-wue-runtime.ps1` (18 checks). The launcher was verified against the
running demo and partial-startup conditions were mocked; a complete laptop-reboot
test has not yet been performed. PostgreSQL must already be installed/running,
and the existing database/migrations/model environment must already be prepared.
Healthy processes are not automatically restarted when source code changes.
If Windows blocks script execution, report the exact error rather than weakening
system-wide execution-policy protections.

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

### October 1 chair-photo test checkpoint

Later rotation-consistency checkpoint (newest frontend result): the CAD views
now project the same center-pivot, Euler-XYZ posed solid used by the 3D viewer.
Traced extrusions are centered before rendering, correcting their former
corner pivot; zero-angle positions remain unchanged. Side/Top tilt direction,
cross-axis dimension coupling, rotated Fit/selection bounds and edge snapping
now follow the projected box. Rotated traced shapes retain their original
outline rather than using a convex hull. Direct drag still moves rotated parts;
canvas resize/outline handles are suppressed for them until inverse-pose editing
is implemented. Use exact Properties for their local dimensions and angles.
Displayed rotated annotations describe projected bounds, not stock dimensions.
No saved finalized model or cost data was rewritten, and no automatic lean
estimate was added. A temporary 8-degree draft slat test was undone and all saved
values verified restored; the draft remains unreviewed. **57 frontend tests
pass**, including actual Three.js extrusion/rotation parity, and build passes
(existing lazy-viewer warning, ~852.86 kB). Worker30/backend348 remain the latest
prior results, not rerun for this frontend-only change. New files:
`frontend/src/lib/componentPose.ts`, `componentPose.test.ts`, and
`frontend/src/features/viewer/profileGeometry.ts`.

Later seat/apron checkpoint (current): `Slatted chair seat-apron test (approx.
size)` has 18 proposed parts, separating front/rear and paired side aprons from
the seat using sustained narrower silhouette bands. Front and back evidence are
independent; side pairing is a stated symmetry assumption. Legs now trace up to
the seat underside instead of stopping below the apron. The seat's projected
height changed from 135.9375 to 77.3438 mm, not a verified physical thickness.
Backrest/slat depth uses median local row spans instead of the swept envelope;
the real set still yields 107.4561 mm rail and 100.8772 mm post/slat estimates
because members overlap in the side photograph. Lean/curvature and hidden
thickness are not solved. No rotation or new 3D representation was introduced.
The new draft remains unreviewed. Front/Back/Left/Right object-bound reference
crops were saved for this copy only (Back/Left mirrored); the angled Top remains
uncalibrated. Earlier 14-part chair was finalized during user testing and is
preserved; initial eight-part comparator stays draft. Table/quote unchanged.
Latest worker result is **30 passing**, with two dependency deprecations. Existing
frontend/build/backend results below remain the latest observed, not new runs in
this worker-only change. Readiness and `git diff --check` pass. The new regression
file is `reconstruction-worker/tests/test_chair_geometry.py`.

- At the initial checkpoint, `Photo reconstruction tests` retained an eight-part draft and `Slatted chair improved proposal (approx. size)`, both unreviewed. The user approved approximate 450 × 900 × 500 mm dimensions. The later checkpoint above supersedes their current status; the retained table demo and quotation are unchanged.
- The improved photo proposal has 14 parts: seat, top backrest rail, two outer backrest posts, six observed middle slats, and four legs. The fitter preserves observed slat columns instead of discarding all but the outer posts. A mask guard now rejects neural masks that expand onto floor/shadow even below the previous dense-fill threshold. Chair Z placement uses the right-side photograph; mirror a left-photo overlay for comparison.
- This is not an accurate manufacturing reconstruction yet: the seat band includes apron pixels, backrest/slat depths are projected envelopes rather than measured timber thickness, and the supplied Top image is angled rather than truly overhead. Photo overlays still need crop calibration. No physical accuracy was measured.
- Photo-analysis feedback checks component source-part identities as well as reconstruction identity. A rerun can replace part IDs under the same reconstruction ID; unmatched analysis now displays a separation notice instead of implying it describes the saved drawing. Manual added parts remain allowed.
- `scripts/probe-photo-set.py` probes five local photos without saving by default. Supplying all three dimensions and explicit `--save-test-copy NAME` imports a separate draft into `Photo reconstruction tests`; it never reviews/finalizes it and rejects duplicate names. `scripts/probe-saved-furniture.py` remains a read-only saved-photo check.
- Initial same-day verification: 43 frontend tests and 23 worker tests pass; production build passes. The later worker result above supersedes 23. Latest full backend result remains 348 passing (backend unchanged during these chair/provenance changes). Existing worker deprecations and large lazy 3D bundle warning remain. Startup readiness passes for worker8010/API8011/frontend5174. Changes remain uncommitted.

### September 30 prototype demo checkpoint

- The separate `Table prototype demo (approx. size)` uses approximate overall dimensions of 1800 × 750 × 900 mm. The original table record and its supplied dimensions were preserved. Approximate sizes demonstrate the workflow, not measured reconstruction accuracy.
- Its reviewed, finalized revision contains nine parts: one tabletop, four legs, and four aprons. Two side aprons were added as explicit manual corrections to the seven-part photo proposal. Finalized geometry remains locked and is shared by 3D, material quantities, and quotation snapshots.
- The editor displays saved photo-analysis notes and supplied dimensions. Strong photo/measurement proportion disagreements are visible warnings; uncertain thickness, depth, hidden joinery, and corrected masks remain review notes.
- Sample catalog entries `DEMO wood - sample price` (100 per board foot), `Wood screw` (2 per piece), and `DEMO labor - sample price` (150 per hour), dated 2026-09-30, are illustrative values, not supplier prices. The BOM, estimate, and saved quote display demonstration-price labels when a DEMO-prefixed resource is selected. The screw identity must remain `Wood screw` for the current calculator.
- The saved demo quotation totals 5,831.51 at display precision: material 5,335.51, screws 16, labor 480. Backend values retain Decimal precision. No currency, tax, markup, or overhead is inferred.
- Dining-table hardware and labor remain the existing v1 assumptions: eight screws and 3.20 hours for this table. Separate apron joints/work, cutting waste, and stock layout are not itemized; the interface now explicitly states these limitations.
- Subsequent table hardening distinguishes stable apron bands from leftover/rounded tabletop pixels. Regression cases cover tables without aprons, missing side-apron evidence, small overhangs, and changed leg spacing. A fresh direct SAM probe of the saved demo photos proposed all nine parts while leaving its finalized plan unchanged; the stored seven-part analysis and manually reviewed plan were not rewritten.
- Latest September 30 verification: 348 backend tests, 18 worker tests, and 35 frontend tests passed; production build passed. Backend test fixtures isolate provider configuration from the local live-AI `.env`. Worker dependency deprecations and the existing large 3D bundle warning remain.
- To test saved photos without creating or modifying a reconstruction/plan/quote, use `.\.venv\Scripts\python.exe scripts/probe-saved-furniture.py <furniture-id>` from the repository root with the API on 8011 and worker on 8010. The probe reuses saved dimensions, checks photo checksums and unchanged saved plans, and explicitly does not verify physical accuracy.

- Canonical axes are X = left/right, Y = vertical, and Z = front/back; the floor is Y = 0.
- Overall dimensions use width = X, height = Y, and depth = Z.
- Finalized 2D geometry is immutable and is the source of truth for deterministic 3D and calculations.
- Calculations use millimeters, cubic millimeters, and backend `Decimal` values.
- Visual appearance and costing material are separate concepts.
- Quotations exclude overhead.
