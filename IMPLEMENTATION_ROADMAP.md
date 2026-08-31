# WUE Codex Edition implementation roadmap

Work proceeds in small, tested modules. Each module receives focused service tests, API tests where relevant, a full regression run, and a clean commit before the next module begins.

Current status: Modules 1 through 7 complete.

1. **Backend foundation (complete)** — FastAPI application factory, environment settings, PostgreSQL/SQLAlchemy session architecture, health endpoints, pytest setup, and project documentation.
2. **Projects and furniture (complete)** — UUID-backed project and furniture models plus CRUD APIs constrained to chair, dining table, and bookshelf.
3. **Furniture images (complete)** — five named views, JPEG/PNG/WebP validation, upload storage abstraction, and camera-ready frontend contracts.
4. **Classification (complete)** — classifier interface, three-class result model, replaceable AI adapter, and deterministic workflow state handling.
5. **Overall dimensions (complete)** — manual-first dimensions, supported-unit conversion, source tracking, and immutability after any 2D plan exists.
6. **Parametric 2D plans (complete)** — canonical X/Y/Z component geometry, type-specific defaults, draft editing, supported manual components, and revision-ready data design.
7. **2D finalization (complete)** — exact semantic validators for each furniture type, immutable finalized plans, and editable successor revisions.
8. **Deterministic 3D** — conversion of finalized components to render geometry, depth/thickness rules, and min-corner-to-center transforms.
9. **Materials and quantity** — admin-managed materials/prices and calculation-only volume estimates using canonical units and `Decimal`.
10. **Material costing** — latest-price selection and conversions for mm3, cm3, m3, and board feet.
11. **Hardware estimation and costing** — documented wood-screw connection rules, validated hardware selection, and `Decimal` costs.
12. **Labor** — separate rate models and transparent, documented WUE v1 hour-estimation rules.
13. **Quotation and admin APIs** — combined material, hardware, and labor totals without overhead; management kept separate from calculators.
14. **Frontend workflow** — React/TypeScript feature modules for projects, images, dimensions, editable 2D, Three.js/R3F viewing, estimates, and quotations.
15. **End-to-end hardening** — real PostgreSQL integration coverage, frontend/backend contract tests, accessibility, error-state polish, and complete regression verification.
