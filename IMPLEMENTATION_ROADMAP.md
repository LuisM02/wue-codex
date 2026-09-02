# WUE Codex Edition implementation roadmap

Work proceeds in small, tested modules. Each module receives focused service tests, API tests where relevant, a full regression run, and a clean commit before the next module begins.

Current status: Modules 1 through 17, the parametric CAD editor, Module 18A, Module 18B1, Module 19A, and Module 19B complete.

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
    - **18B2 — local pretrained inference worker (next):** replace baseline foreground extraction with SAM 2, then sequentially run pose-free multi-view geometry, part proposals, cross-view fitting, and uncertainty scoring on the RTX 4070 laptop GPU. Licensed checkpoints remain deliberately separate until approved.
    - **18C — furniture-part fine-tuning:** render licensed part-annotated furniture data, collect user-corrected real WUE profiles, train/evaluate the smaller part detector, and version its dataset/model rather than attempting to train a 3D foundation model from scratch.
19. **End-to-end hardening**
    - **19A — isolated real PostgreSQL verification (complete):** each integration session creates, migrates, tests, and removes a uniquely named disposable database, so retained rows in a shared test database cannot contaminate results. The complete 332-test backend suite passes on PostgreSQL 18.
    - **19B — contract and accessibility hardening (complete):** a shared manifest is exercised by every frontend API method and checked against FastAPI OpenAPI; expected optional 404s remain quiet while genuine partial-load failures identify the affected resource. CAD toolbar/toggle/status semantics and keyboard-only selection were verified in the live app.
    - **19C — release regression (next):** run the complete backend, worker, frontend, production-build, and browser workflow matrix before the AI training phase.
