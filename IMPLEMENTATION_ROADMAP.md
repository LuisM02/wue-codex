# WUE implementation roadmap

October 1 terminal-face follow-on (newest): backed-bookshelf bottom thickness
prefers its own coherent front-face edge pair below the detected interior
shelves. Missing lower/cap boundaries and missing terminal onset receive
specific provisional warnings; the fallback is not presented as measured.
Worker46 tests pass (two existing deprecation warnings). The live SAM bookshelf
probe remains nine parts with unchanged ambiguous terminal estimates; table
probe remains nine parts. Both probes verify saved plans unchanged. Backend377,
frontend65 and build-pass are preceding unchanged-module results, not rerun here.
Worker safely reloaded; readiness passed. No dependencies, schema, endpoints,
training, automatic finalization or cross-view depth fitting were added.
The nine-part bookshelf comparison remains an unreviewed draft. Next: review
its part boundaries and obtain real overall/stock dimensions; avoid treating
the reused 450 × 900 × 500mm scale as accuracy evidence.

October 1 failure-feedback follow-on (preceding): worker input rejection now maps
to API422 through separate domain exceptions, not an invalid-output502. Worker
configuration/busy/unavailable faults remain503; malformed results/errors remain
502. Transport timeouts have explicit bounded reasons. UI retains the worker
reason with corrective/service guidance and no longer claims the connected
provider is absent. Manual selection stays a clearly labeled testing action,
not an AI result or reconstruction substitute. Fresh backend377/frontend65/build
pass; worker42 remains unchanged latest prior observation. Regression verifies
failed requests leave saved recognition, analysis and plans unchanged. API alone
reloaded; five retained plan statuses and sample quote checked read-only. No
new geometry, training, dependencies, endpoints, schema or pricing changes.

October 1 bookshelf follow-on (latest): implemented a solid-back internal-edge
path with bounded, coherent opposite-contrast shelf faces; stable frame bounds
prevent a bottom leg fragment becoming a narrow bottom panel. Removed the guessed
middle-shelf fallback. A SAM probe of the actual bookshelf photos now detects
four interior shelves/nine parts and leaves the saved finalized plan unchanged.
A separate nine-part draft in Photo reconstruction tests is unreviewed; the
existing six-part bookshelf remains finalized. Worker42 tests pass, including
HTTP explicit failure, altered shelf count/position/thickness, polarity, grain,
short objects and one-pixel noise. Backend348/frontend57/build-pass remain the
latest preceding full checkpoint results, not rerun for this worker-only change.
No trained semantic recognition, cross-view depth fitting, accuracy benchmark,
new dependency or API/database/frontend change was added. Next: user review of
the new draft and physical thickness/scale evidence before finalization.

Work proceeds in small, tested modules. Each module receives focused service tests, API tests where relevant, a full regression run, and a clean commit before the next module begins.

Current status: Modules 1 through 17, the parametric CAD editor, Module 18A, Module 18B1, Modules 19A through 19C, and Modules 20 through 25 complete. Version 0.25.0 is the verified metric photo-calibration baseline.

October 1 subsequent checkpoint: a separate approved approximate-size chair test
now preserves six visible middle slats (14 proposed parts), rejects expanded
floor/shadow masks, and uses the right elevation for chair Z placement. Both the
initial eight-part draft and improved proposal remain unreviewed; the table demo
is unchanged. Seat/apron separation, stock thickness, curved/leaning backrest
depth and physical accuracy remain incomplete. Side-table aprons independently
use side evidence. Feedback now verifies source-part identities so a same-ID
analysis rerun cannot be mistaken for the saved drawing's original proposal.
Latest observed: 43 frontend and 23 worker tests pass, build passes, startup
readiness passes. Latest full backend result remains 348 passing; no backend
changes in this checkpoint. This dirty working state is not a clean commit.
Next priority: correct these chair geometry failures in a separate draft, align
reference crops, obtain real measurements when possible, and rehearse the
retained end-to-end demo before defense; defer risky new training architecture.

Later October 1 follow-on: independent visible apron evidence now separates four
chair aprons from the seat, and legs reach its underside. A third comparison
copy (`Slatted chair seat-apron test (approx. size)`) has 18 parts, remains draft,
and has four elevation reference crops; angled Top is uncalibrated. Median row
depth reduces the swept-envelope error but the real overlapping slats remain
over-thick, so this portion is only partially resolved. Worker tests now **30
passed**. Prior frontend43/backend348/build results remain latest observed;
none of those code modules changed in this follow-on. Table read-only probe,
runtime readiness and diff whitespace check pass. The earlier 14-part chair is
now user-finalized, preserved rather than rebuilt. Next: user review plus
measured stock thickness/true overhead evidence when available; straight
extrusion cannot yet reproduce rear lean or curved rail depth exactly.

September 30 subsequent hardening checkpoint: stable-band table apron detection
now rejects slab-only false panels while retaining small-overhang aprons. A fresh
SAM probe of the real demo photos proposes nine parts without changing the saved
finalized plan. The latest full regression passes 348 backend, 18 worker, and 35
frontend tests plus the production build. Earlier test totals below are historical
module checkpoints. Reconstruction accuracy evaluation and neural semantic part
recognition remain incomplete; this checkpoint is not a new accuracy claim.

Windows demo recovery now has an explicit local startup/readiness script at
`scripts/start-wue.ps1`, with worker8010/API8011/frontend5174, conflict-safe
service reuse, database/proxy/GPU-provider checks, and ignored local logs. Its
18 safety checks pass and repeated startup was verified against healthy services.
Full laptop-reboot recovery remains to be exercised; no installation, migration,
automatic conflicting-process shutdown, or database reset is included.

1. **Backend foundation (complete)** — FastAPI application factory, environment settings, PostgreSQL/SQLAlchemy session architecture, health endpoints, pytest setup, and project documentation.
2. **Projects and furniture (complete)** — UUID-backed project and furniture models plus CRUD APIs constrained to chair, dining table, and bookshelf.
3. **Furniture images (complete)** — five named views, JPEG/PNG/WebP validation, upload storage abstraction, and camera-ready frontend contracts.
4. **Classification (complete)** — classifier interface, three-class result model, replaceable AI adapter, and deterministic workflow state handling.
5. **Overall dimensions (complete)** — manual-first dimensions, supported-unit conversion, source tracking, and immutability after any 2D plan exists.
6. **Parametric 2D plans (complete)** — canonical X/Y/Z component geometry, type-specific defaults, draft editing, supported manual components, and revision-ready data design.
7. **2D finalization (complete)** — exact semantic validators for each furniture type, immutable finalized plans, and editable successor revisions.
8. **Deterministic 3D (complete)** — read-only conversion of finalized components to render geometry, exact depth/thickness fallback, and min-corner-to-center transforms.
9. **Materials and quantity (complete)** — admin-managed materials and dated price history plus calculation-only volume estimates using canonical units and `Decimal`.
10. **Material costing (complete)** — calculation-only latest-price selection and Decimal conversions for mm3, cm3, m3, and board feet.
11. **Hardware quantity estimation (complete)** — documented calculation-only wood-screw connection rules with no 3D prerequisite.
12. **Hardware costing (complete)** — validated hardware selection, latest per-piece pricing, and `Decimal` costs.
13. **Labor quantity estimation (complete)** — calculation-only, transparent WUE v1 hour assumptions derived from finalized component semantics.
14. **Labor rates and costing (complete)** — separate admin-maintained hourly rates, dated history, and `Decimal` labor costs.
15. **Quotation and admin APIs (complete)** — exact material, hardware, and labor totals without overhead plus immutable historical snapshots.
16. **Frontend workflow (complete)** — responsive React/TypeScript feature modules for projects, five-view images, dimensions, editable 2D plans, lazy-loaded Three.js/R3F viewing, estimates, and immutable quotations.
17. **Photo-first workflow and guided part editing (complete)** — furniture starts unclassified, plan generation waits for recognition, source-image changes invalidate derived identity, and the 2D workspace guides users through one highlighted part at a time with live size and position previews plus an optional photo overlay.
    - **Parametric CAD editor (complete):** desktop three-panel workspace with canonical Front/Side/Top projection, direct drag and resize, exact properties, grid and edge snapping, zoom/pan, dimensions, contextual part creation, semantic warnings, bounded Undo/Redo, backend persistence with rollback, and finalized read-only inspection.
18. **Vision reconstruction provider**
    - **18A — photo-derived reconstruction contract (complete):** persist input-photo signatures, provider/model provenance, warnings, per-part source views and confidence, editable traced profiles, and full rotations. Initial plan creation now requires this result and never calls the old generic template generator. Source changes invalidate reconstruction. Profile outlines drive 2D, 3D extrusion, and polygon-area material quantity.
    - **18B1 — runnable local silhouette worker (complete):** isolated health/model-status, automatic three-class recognition, checksum and five-view validation, opposite-view consistency checks, wrong-orientation rejection, photo-specific silhouette tracing, side-depth fitting, semantic structural regions, confidence/warnings, and HTTP integration. This dependency-light baseline is intentionally identified as non-neural and works best against a plain background.
    - **18B2 — local pretrained inference worker (in progress):** the provenance-aware SAM 2.1 adapter now runs its official Base Plus checkpoint in an isolated Ubuntu 24.04 WSL environment on the RTX 4070. A five-view WUE endpoint run verified CUDA inference, eleven editable chair parts, and exact checkpoint-hash reporting. Pose-free multi-view geometry, neural part proposals, cross-view fitting, and uncertainty scoring follow. MASt3R-family geometry checkpoints remain deliberately separate because their non-commercial and training-dataset licenses need approval.
    - **18C — furniture-part fine-tuning:** render licensed part-annotated furniture data, collect user-corrected real WUE profiles, train/evaluate the smaller part detector, and version its dataset/model rather than attempting to train a 3D foundation model from scratch.
19. **End-to-end hardening**
    - **19A — isolated real PostgreSQL verification (complete):** each integration session creates, migrates, tests, and removes a uniquely named disposable database, so retained rows in a shared test database cannot contaminate results. The complete 337-test backend suite passes on PostgreSQL 18.
    - **19B — contract and accessibility hardening (complete):** a shared manifest is exercised by every frontend API method and checked against FastAPI OpenAPI; expected optional 404s remain quiet while genuine partial-load failures identify the affected resource. CAD toolbar/toggle/status semantics and keyboard-only selection were verified in the live app.
    - **19C — release regression (complete):** version 0.25.0 passes all 348 backend tests on PostgreSQL 18, all 12 reconstruction-worker tests, all 33 frontend tests, and the optimized production build. Its focused CAD verification covers normalized crop conversion, persisted API calibration, PostgreSQL crop constraints, view-aware source selection, and the existing traced-part editor.
20. **BOM-first costing workflow (complete)** — a dedicated post-3D bill of materials separates engineering quantities from the commercial quote, shows material and hardware summaries plus a per-part audit, carries selected purchasing stock into quotation costing, and provides first-run local wood, screw, and labor price setup without inventing market prices.
21. **Human part-review gate (complete)** — every newly reconstructed draft opens with its front photograph and editable AI parts, records an explicit user confirmation, blocks finalization until that review exists, preserves approved copied revisions, and resets review when a revision is rebuilt from new photo analysis.
22. **Traced-outline control points (complete)** — selected photo-derived polygons expose draggable Front-view vertices over the reference image, preserve point order and valid area, clamp edits to the component bounds, support optional 5 mm snapping, participate in Undo/Redo, and persist through the existing component API so the same edited outline drives 3D extrusion and material volume.
23. **Outline topology and validity (complete)** — users can insert a midpoint after a selected vertex or on the longest edge, remove a selected vertex while retaining a valid polygon, and identify the active point visually or by keyboard. Shared frontend guards and authoritative backend validation reject zero-area, repeated-edge, or self-intersecting profiles before they can reach 3D or costing; invalid merged updates return HTTP 422.
24. **Multi-view reference overlays (complete)** — Front can use Front/Back, Side can use Left/Right, and Top uses Top while every view continues editing one canonical X/Y/Z model. The current photograph can be toggled, switched, or mirrored independently without mutating stored images or geometry. View-aware reference selection is unit-tested and the live saved chair resolves each source through its verified image-content endpoint. These overlays are visual review aids, not perspective-correct metric measurements.
25. **Metric photo calibration (complete)** — every uploaded view persists a normalized visible-furniture crop plus horizontal mirror state. The CAD calibration panel accepts left, right, top, and bottom photo margins, previews the alignment, validates that a visible object remains, and maps the resulting crop onto the measured overall width/height/depth bounds for Front, Side, and Top. Calibration is reusable across plan revisions and does not alter the source image, canonical component geometry, or AI input signature. This is an object-scale alignment aid, not camera pose estimation or perspective correction.

October 1 rotation-consistency follow-on (newest frontend checkpoint): fixed
traced 3D profiles rotating about a corner while CAD used a center, plus reversed
Side/Top tilt signs. CAD now projects the center-pivot Euler-XYZ solid, including
depth/height coupling and rotated selection/Fit/snap bounds, using existing
rotation fields and no new dependencies/API/database schema. Properties remain
editable; direct canvas resize/profile handles are intentionally unavailable for
rotated parts until inverse-pose edits can be implemented safely. The temporary
8-degree slat test was undone and API readback confirms all saved values restored
and review null; no actual chair lean was inferred or persisted. Latest frontend
suite **57 passing**, production build passes; lazy viewer warning ~852.86 kB.
Latest prior worker30/backend348 unchanged, not rerun here. Next: supported
photo-driven lean estimation and independently constrained stock thickness;
curved-depth geometry and physical accuracy remain incomplete. Finalized source
of truth and human review gate stay intact.
