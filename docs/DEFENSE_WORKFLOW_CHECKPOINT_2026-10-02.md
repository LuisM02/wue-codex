# Defense workflow checkpoint — October 2, 2026

## What was completed

The existing finalized table was inspected through its 3D preview, BOM and
quotation screens. The actual browser rendered the model, showed nine physical
pieces, selected the demo wood/screw/labor resources and calculated 5,831.51.
The pre-existing quotation remains visible. No quotation was created or printed;
no new draft was confirmed, finalized, edited or rebuilt by this check.

The current audit table was inspected with the explicit Left view and matching
Left photo. Its retained side-apron Y position is 623.7250 mm with height
77.5251 mm. It is still a **draft with no recorded parts review**. Inspection
does not certify its stock dimensions, photo alignment or hidden construction.

## Reusable verification tool — IMPLEMENTED

- `scripts/check-defense-demo.py`: read-only local checker with finalized plan
  and quotation UUID arguments, plus optional `--draft-plan-id`.
- `scripts/tests/test_check_defense_demo.py`: 17 controlled tests; no live HTTP
  calls. They cover coherent box/profile volumes, dimensional/placement/center/
  rotation drift, duplicate IDs, volume/cost discrepancies, GET-only behavior,
  draft guards, and catalog-price edits that must not invalidate a historical quote.
- CLI errors explain offline/timeout/HTTP/consistency failures without a
  traceback, return exit code1, and state that no write requests were issued.
- This tool does not modify the app, prices, approvals or database. It does not
  invoke inference, train AI, compare a model to physical measurements, or
  simulate production loads. New API endpoints and dependencies: **none**.

Run from the active repository in PowerShell using the existing environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\check-defense-demo.py 3d7942f9-601e-4e34-a983-d530f79f0e6e 958c2049-e1f2-4cc8-9cc7-1e0ea54c4021 --draft-plan-id c6e4f0c6-17fa-486d-acc5-4b64038fa479
.\.venv\Scripts\python.exe -m pytest .\scripts\tests -q
```

These IDs refer to this laptop's saved demo. Another installation must supply
its own finalized plan and quotation IDs; the checker does not create fixtures.
Failures stop with an error. If a source changes during the check, investigate
concurrent editing rather than restoring/overwriting that record automatically.

## Actual verified results

- Finalized table: furniture `9aefb16b-cbb0-4e8c-969b-34869d80a87b`, in project
  **Dining** (`da6d391c-f597-4e80-befc-b414efbf1507`), named
  **Table prototype demo (approx. size)**.
- Source plan `3d7942f9-601e-4e34-a983-d530f79f0e6e`, finalized revision 1,
  nine components/pieces. This is the preserved earlier design, not a newly
  saved result from the 0.3.1 table mapping probe.
- `/geometry-3d` source IDs, geometry kind, profile points, dimensions,
  min corners, center coordinates, XYZ rotations and quantities match that plan.
- `/material-quantity` agrees with independently recomputed box/polygon area
  multiplied by depth and quantity. This is numerical consistency of the
  reviewed model, **not verified real-world timber requirements**.
- Saved quote `958c2049-e1f2-4cc8-9cc7-1e0ea54c4021` references the same revision.
  Its 53.35512941768641009728432405246262810986 board ft at 100 per board ft
  gives 5,335.512941768641009728432405246262810986; eight screws at 2 each
  give 16; assumed labor 3.20 hours at 150 gives 480. Total at display precision:
  **5,831.51**. No currency, tax, markup or overhead is assigned.
- Current price IDs, units and numeric rates still match the saved quote;
  `GET /complete-cost` matches its total. Historical snapshots are not rewritten
  if an administrator later edits a catalog price.
- Audit plan `c6e4f0c6-17fa-486d-acc5-4b64038fa479` remains draft/unreviewed.
  `GET` geometry-3d, material-quantity, hardware-quantity, labor-quantity and
  complete-cost each return409. No POST finalization test was made on live data.
- Checked finalized plan, quote and audit draft were equal immediately before
  and after the checker. Existing user position edits were preserved.

Fresh test results: **381 backend tests**, using a disposable sibling PostgreSQL
test database; **115 frontend tests across 14 files**; **17 standalone checker
tests**. TypeScript/production build passes, with the unchanged 852.86kB lazy
viewer-chunk warning. Worker suite's preceding result is **66 passed** at
pipeline 0.3.1; it was not rerun for this tool/documentation-only revision.
On resuming, all three existing services were stopped and the normal launcher
started them; API/database/proxy/SAM readiness and the live checker passed again.
No migration, dependency installation, live data reset or process termination occurred.

## Defense rehearsal sequence — not a completion claim

1. Open **Dining → Table prototype demo (approx. size)**. Explain that this is
   a saved demonstration using approximate overall dimensions and sample rates.
2. Show the five reference photos. Explain that pretrained SAM 2.1 assists
   foreground masks, with deterministic heuristics for furniture structure and
   parts. It is not a student-trained semantic part detector or exact automatic
   reconstruction. Do not rerun analysis on protected saved data just to rehearse.
3. Show the locked 2D revision in Front, Back, Left, Right and Top. Explain that
   corrections occur in a draft, and finalized geometry is the shared source
   for downstream work. The shape score is not an accuracy percentage.
4. Show the corresponding 3D; appearance/finish selection does not select
   costing stock. This is profile extrusion and bounded geometry, not proof
   that every hidden face matches the original furniture.
5. Show BOM purchasing choices, net modeled volume, part breakdown and the
   explicit prototype hardware rule. There is no sheet nesting or cutting waste.
6. Calculate the demo quote; show wood, screw and labor breakdowns and the
   existing immutable record. The current table rules count leg fasteners and
   base/leg/top work; **separate apron joints and apron labor are not itemized**.
   Do not describe this as a supplier/manufacturer-approved final quotation.
7. Show the unreviewed audit draft's disabled downstream steps. Only after the
   user reviews its actual shapes, placements and provisional depths should
   review and finalization be recorded. Do not approve it on the user's behalf.

## Still required / must not be reverted

- User-led review of the current draft is pending. Physical dimensions, hidden
  stock depths, construction safety and generalization accuracy are unverified.
- Whole-PC reboot recovery, a fresh recorded walkthrough and updated submission
  backup are not verified by this checkpoint. The October 1 submission zip is
  older than the October 2 editor and worker revisions.
- Keep the five explicit views, explicit single-active-point outline editing,
  independent side mapping and honest mismatch message. Preserve all finalized
  source plans, sample quote, and the audit draft's independent position edits.
- Do not overwrite earlier audit snapshots to hide concurrent user edits.
- This is verified evidence for later paper-source consolidation, not an upload
  to the shared paper project or a claim that all approved thesis objectives,
  rubric criteria, privacy/security, scalability or measured accuracy are met.
