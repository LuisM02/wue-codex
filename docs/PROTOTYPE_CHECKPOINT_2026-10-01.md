# WUE prototype checkpoint — October 1, 2026

## Latest two-side chair lean checkpoint

- IMPLEMENTED: `reconstruction-worker/wue_worker/chair_pose.py` fits a straight
  backrest centerline only when mirrored Left and Right silhouettes agree.
  Stable contiguous row coverage, width stability, residual, angle (up to18°),
  cross-view angle/placement and rotated overall-bound checks are required.
  Effectively upright evidence gets no cosmetic rotation. Failure preserves
  upright geometry and adds a review warning; it never partially tilts/clips
  an assembly or substitutes a standard chair.
- IMPLEMENTED: eligible detected `left_backrest_post`, `right_backrest_post`
  and `backrest_slat_*` receive `rotation_x`. Their center-pivot geometry keeps
  the previous front-view vertical envelope and side-row cross-section; local
  X/Y profile points rescale with the adjusted height. The existing 2D/3D pose
  convention remains the source-of-truth rule. Top rail (`backrest`), legs,
  seat and aprons do not receive automatic tilt. Rail/leg connections need review.
- PARTIALLY IMPLEMENTED reconstruction fidelity: the actual supplied slatted
  chair's SAM analysis estimates **8.5062°** on eight of18 parts. Approximate
  overall450 × 900 × 500mm scale and unrectified views do not establish a physical
  angle. Post/slat depth is still an overlapping envelope (about99.8mm), not
  measured stock; seat thickness, curved rail, rear legs and joinery remain
  provisional. This is not training, exact reconstruction or measured accuracy.
- Separate test copy: furniture `a60d1aa5-6b5f-4f73-8d9c-8bacb1b6d1d0`, name
  `Slatted chair two-side lean test (approx. size)`, plan
  `74eeae5f-8cde-4833-8893-53ee5d753776`, **draft,18 parts,
  parts_reviewed_at null**. All five photo checksums matched the retained chair
  before copying its four front/back/left/right display alignments to the new
  copy only. Top alignment was not copied. Alignment is display metadata, not
  camera calibration or new geometry evidence. Existing copies were not rebuilt.
- Fresh regression: **backend379 passed, no warnings; frontend85 passed across
  12 files; worker56 passed** with two existing Starlette/AnyIO deprecations.
  Production build passed with the existing852.86kB lazy 3D viewer warning.
  Backend tests verify box/profile poses and source IDs survive proposal→draft→
  user review→finalized3D, and draft3D/unreviewed finalization remain blocked.
  Those approval actions occur only in disposable test databases, not live demos.
- Live checks: new chair Side view shows the8.5062° tilt in Properties and uses
  the existing rotated-part projected-bound annotations/handle restrictions.
  Left/Right comparison and zoom work without geometry edits or review. It is
  left on Right photo, selected left backrest post,144%zoom. Screenshot outside
  Git: `C:\Users\Luis Mendoza\Documents\ChatGPT\wue codex edition\wue-chair-two-side-lean.jpg`.
  Readback confirms draft/null review and eight tilted parts. Actual read-only
  table/bookshelf SAM probes still return nine parts each and verify saved
  plans unchanged; confidence/part counts are not accuracy percentages.
- Retained finalized table plan `3d7942f9-601e-4e34-a983-d530f79f0e6e`, both
  finalized18-part chair plans, original six-part bookshelf and unreviewed
  nine-part bookshelf are preserved. Sample quote
  `958c2049-e1f2-4cc8-9cc7-1e0ea54c4021` still totals5,831.51 at display precision,
  with sample wood100/board_ft, screw2/piece and labor150/hour. No currency,
  supplier-price accuracy, manufacturing safety or waste/nesting claims added.
- Services began stopped; the existing launcher started worker8010, API8011
  and frontend5174 without migrations, installations, resets or terminating
  unrelated processes. API/database/proxy/SAM GPU readiness passed. Whole-PC
  reboot recovery remains untested. No schema, endpoints, dependencies or
  pricing rules changed; the probe script now reports `part_poses` as well.

Next defense priorities: the user reviews/corrects new draft stock dimensions,
depths and rail/leg connections; only the user confirms/finalizes when satisfied.
Rehearse the retained table's finalized2D→3D→BOM→sample quote, prepare separate
local database/uploads backups, and present assisted reconstruction honestly.
This checkpoint does not claim the whole defense preparation is finished.

## Preceding CAD part-by-part inspection checkpoint

- IMPLEMENTED: photo-derived drawings show a part-by-part guide. Previous/Next
  follows the current component list without wrapping; no selection can restart
  at the first part. Buttons select available comparison photos in Front/Back,
  Left/Right and Top groups, prefer recorded source views and reset fit/pan.
  A comparison photo is not added to the saved AI source metadata.
- IMPLEMENTED: Show only this part hides other SVG shapes but keeps all model
  components, full-furniture scale, photo alignment and snapping context.
  Selection/property/outline editing continues under the existing draft rules.
  Isolation resets on plan/status change and falls back to all shapes when
  nothing is selected. Finalized drawings remain read-only.
- Plain-language bookshelf checks distinguish shelves, terminal panels, sides
  and backing; renamed/other furniture parts get generic identity/shape/depth
  checks. Current local sizes are model values, not verified measurements.
  The inspector labels proposal confidence as not reconstruction accuracy,
  including zero-confidence values. Neither navigation nor isolation records
  review, and no new completion/accuracy percentage is presented.
- New files: `frontend/src/features/plans/cad/partReview.ts`,
  `PartReviewGuide.tsx`, `partReview.test.ts` in the same directory. Modified:
  `Furniture2DEditor.tsx`, `CanvasWorkspace.tsx`, `PropertiesPanel.tsx` in that
  directory, plus `frontend/src/styles.css` and checkpoint docs.
- Fresh verification: **85 frontend tests passed across12 files**, production
  build passed. Existing lazy viewer chunk warning remains852.86kB. One initial
  isolation test compared the first rendered shape (an unselected bottom) to
  the selected shelf; its selector was corrected, then the final suite passed.
  Backend377 and worker46 are previous unchanged-code results, not rerun here.
- Live browser checks on the nine-part bookshelf draft: next/previous selection,
  last-part navigation boundary, source-preferred front photo and side/top photo
  switching, isolation and shelf-specific notes passed. DOM shape count was1
  while isolated; all nine saved components remain. Read-only before/after API
  JSON comparison confirmed every saved plan field identical, including
  `status = draft`, `parts_reviewed_at = null`. No geometry, alignment,
  classification, analysis, confirmation or finalization was saved by testing.
- Screenshot is local, outside Git:
  `C:\Users\Luis Mendoza\Documents\ChatGPT\wue codex edition\wue-part-review-guide.jpg`.
  The app is left on shelf1, Front photo, isolation enabled and guide notes open.
  The user can toggle isolation off; it is not a deleted-parts view.

This is a review-usability improvement, not new inference, physical accuracy,
training or camera calibration. Existing review/finalization gates, APIs,
database schema and dependencies are unchanged. Next: user compares the draft
with photos, corrects provisional size/depth/shape, then confirms and finalizes
only when satisfied. Do not do those approval actions on their behalf.

## Latest bookshelf terminal-face checkpoint

- IMPLEMENTED: the backed-bookshelf bottom panel prefers an independently
  observed coherent opposite-edge pair below the interior shelves, with the
  same onset polarity. It no longer always copies the interior shelf median
  when its own face is distinguishable. Foreground coverage, contrast,
  thin-face bounds and shadow suppression remain required; detection thresholds
  were not weakened. Interior shelf detection remains unchanged.
- Explicit warnings identify copied bottom thickness, missing top-cap boundary
  and missing bottom onset. A visible face remains a projected estimate, not
  a measured physical thickness. Side/back depth, back thickness and joinery
  are still provisional.
- Changed implementation: `reconstruction-worker/wue_worker/geometry.py`;
  changed tests: `reconstruction-worker/tests/test_bookshelf_geometry.py`.
  Four added controlled tests verify independent terminal thickness, unchanged
  interior/back geometry, explicit fallback and terminal/interior separation.
- Fresh worker result: **46 passed**, two existing Starlette/AnyIO deprecation
  warnings. Backend377/frontend65/build-pass are the previous checkpoint's
  results; those unchanged modules were not rerun here. Whitespace check passed.
- Only the verified worker on8010 was reloaded. The first launcher check caught
  its transient shutdown listener and safely refused to start; a retry after
  confirmed exit succeeded. API/frontend stayed healthy; database/proxy/SAM GPU
  readiness passed. No installations, migrations or resets occurred.
- Live read-only SAM probes: bookshelf remains four interior shelves/nine parts;
  top/bottom remain14.4mm because their independent boundaries are ambiguous.
  New fallback warnings explain this, rather than claiming better accuracy on
  these inputs. Table remains nine parts. Both probes verified saved plans
  unchanged and report `accuracy_verified = false`.
- Existing stored reconstruction notes were not replaced by these probes.
  Updated notes apply to future analysis; do not silently rerun saved finalized
  furniture just to refresh them. The nine-part bookshelf comparison remains
  draft with null review timestamp. Six-part bookshelf, nine-part table and
  fourteen-/eighteen-part finalized chair plans are preserved. Readback also
  includes finalized chair plan `69c6ef6d-fd24-445a-a408-fe87684acf92`, eighteen
  parts, user-reviewed at `2026-10-01T13:05:17.273019+08:00`; it was not changed.

Next: user reviews the comparison draft against the photographs and supplies
physical size/stock thickness when possible. Do not finalize on the user's
behalf, claim exact reconstruction or interpret controlled fixtures as an
accuracy benchmark. No new schema, API payload, dependency or training added.

## Latest photo-analysis failure feedback

The local worker was already returning bounded text details, but its photo
rejections were labeled API502, and the photo UI incorrectly described every
503 as an unconnected provider. This follow-on corrects that distinction.

- New domain exceptions: `ClassificationInputRejectedError` and
  `ReconstructionInputRejectedError`. Worker400/422 with valid text details
  become API422. Invalid/malformed worker output or rejection details stay502.
  Configuration/busy/unavailable worker failures stay503. Timeouts explicitly
  report that no new result/drawing was saved.
- Existing POST `/api/v1/furniture/{furniture_id}/classification` and
  POST `/api/v1/furniture/{furniture_id}/reconstruction` paths/payloads are
  unchanged. This is an intentional status distinction, not a new endpoint.
- `frontend/src/lib/photoAnalysisError.ts` retains reasons and distinguishes
  input correction, incomplete prerequisites, unavailable services, and invalid
  output. Plan-creation errors are kept separate from photo-analysis errors.
- Manual type selection is labeled as testing/correction, not an AI result;
  choosing a type does not fix an unavailable photo reconstruction service.
- Fresh regression: **377 backend passed**, no new warnings; **65 frontend
  passed**, 11 files; production build passed with existing ~852.86kB lazy viewer
  warning. Worker42 is the unchanged preceding result, not rerun here.
- Failure cases verify saved classification/type, reconstruction/source parts,
  and plan contents are unchanged. Backend tests use a disposable PostgreSQL
  sibling database; no live demo inference was deliberately failed.

Only the verified API on8011 was reloaded. Worker/frontend remained active;
readiness passed. Read-only API checks preserve the nine-part bookshelf draft,
six-part finalized bookshelf, nine-part finalized table, fourteen- and
eighteen-part finalized chairs, and sample quotation. The new bookshelf draft
still requires user review before finalization/3D. No new geometry, training,
dependency, database migration, pricing rule or automatic finalization was added.

## Subsequent bookshelf checkpoint

Worker-only follow-on corrects the solid-backed bookshelf failure: internal
contrast edges now propose the four photographed shelves (nine parts total)
instead of the earlier guessed single shelf. Stable frame bounds and full
interior width replace the erroneous narrow bottom-panel trace. Missing shelf
evidence returns HTTP422 instead of inserting a guessed middle shelf. Existing
open-shelf regression remains passing. No new neural model/training is involved.

Fresh worker result: **42 passed**, two existing deprecation warnings. Previous
backend348/frontend57/build-pass results below remain the latest full checkpoint;
those unchanged modules were not rerun for this scoped follow-on. The actual
SAM-backed five-photo probe reports `saved_plans_unchanged = true` and
`accuracy_verified = false`.

Original bookshelf furniture `32fa721f-0cfd-4d4c-931d-a2d7f9970bef`, plan
`8b8f8a25-d4e0-4099-9aad-b2dbb0ac7fab`, remains finalized with six parts.
Separate comparison furniture `07d3bca1-c406-485f-abf2-dc597100a882`, name
`Bookshelf internal-edge test (saved scale)`, in `Photo reconstruction tests`,
has draft plan `d37157f2-0f29-483e-a436-43cc782ad203` with nine parts and
`parts_reviewed_at = null`. It reuses the original entered 450×900×500 mm;
the scale is not validated by physical measurement. No user review gate was bypassed.

Shelf location/thickness follows front contrast edges, but side/back depth,
back thickness, terminal thickness, joinery, perspective and floor shadows still
require review. Decorative horizontal bands can resemble shelves. This is a
bounded image-analysis improvement, not an exact reconstruction guarantee.
The new draft is the next user review target; preserve all earlier demos.

Latest API readback also shows chair plan `3fe6f55a-d667-4f94-95ea-f20c56193bc1`
is now finalized with eighteen parts, reviewed at
`2026-10-01T13:07:14.169833+08:00` during user testing. Earlier mentions of its
unreviewed status below are historical. The agent did not finalize it. A fresh
table probe still proposes nine parts and leaves its saved plans unchanged.

This checkpoint saves the changes after `7db4ef8`. It is not a claim of
measured reconstruction accuracy or production readiness.

## Included changes

- Persisted photo alignment crops and mirroring, bounded by API validation and
  PostgreSQL constraints. Migration: `20260918_0012_add_image_calibration.py`.
  Alignment is display metadata, not camera/perspective calibration; it does
  not replace the photographed input or invalidate unchanged AI inputs.
- Photo-analysis feedback with source-part identity checks. New analysis must
  not be presented as describing an older saved plan when its source parts differ.
- SAM foreground safeguards for chairs with open space; chair slat/post
  preservation; independent apron evidence for tables and chairs; seat/apron
  separation and median side-row depth estimates.
- Consistent center-pivot Euler XYZ rotation for CAD Front/Side/Top projections
  and Three.js box/profile geometry. Rotated bounds are labeled as projected
  bounds. Rotated parts can be moved and edited through Properties; direct
  resize/outline handles are deliberately unavailable for those parts.
- Clear sample-price notices and net-volume/hardware/labor limitations in BOM
  and quotation screens. No tax, markup, overhead, or cutting-waste calculation
  was added.
- Local Windows startup/readiness safeguards and read-only photo probing.
  Saving a separate test copy requires explicit `--save-test-copy` opt-in.
- WUE project titles and the `wue-frontend` package name replace the former
  edition/package branding. Existing local directories and database identifiers
  are retained for compatibility; branding changes do not rename or migrate them.

## Fresh verification (earlier full checkpoint; see latest results above)

- Backend: **348 passed**, including real PostgreSQL tests using a uniquely
  named disposable sibling database. Application/demo records are not test targets.
- Frontend: **57 passed** in 10 files.
- Reconstruction worker: **30 passed**.
- Production build: **passed**. Existing lazy 3D viewer chunk warning remains
  (approximately 852.86 kB); it is not a build failure.
- Worker: two existing Starlette/AnyIO deprecation warnings remain.
- Startup safety: **18 checks passed** without changing WUE services.
- Startup from all three stopped WUE services: **passed**; worker, API,
  database, frontend proxy, and SAM GPU provider became ready. No migrations,
  installation, data reset, or conflicting-process termination was performed.
- Whitespace verification: `git diff --check` passed.

## Retained local demo state

These records are local database state, not fixtures or backups committed to Git.
Uploaded photos, the database, `.env`, model checkpoints, generated builds,
virtual environments, and local runtime logs are excluded from the source push.

- Dining-table demo: furniture `9aefb16b-cbb0-4e8c-969b-34869d80a87b`,
  finalized plan `3d7942f9-601e-4e34-a983-d530f79f0e6e`, nine parts. Its
  approved approximate dimensions are 1800 × 750 × 900 mm.
- Existing sample-price quotation `958c2049-e1f2-4cc8-9cc7-1e0ea54c4021`
  displays 5,831.51; no currency is assigned by the model.
- Earlier fourteen-part chair plan `13fd5bce-0a74-445a-a176-58afee54fda5`
  was finalized during user testing. Preserve it rather than rebuilding it.
- Current eighteen-part chair plan `3fe6f55a-d667-4f94-95ea-f20c56193bc1`
  is now finalized, user-reviewed at `2026-10-01T13:07:14.169833+08:00`.
  Approximate overall size: 450 × 900 × 500 mm. Earlier draft descriptions
  are historical; the agent did not confirm or finalize on the user's behalf.
- The temporary 8-degree UI rotation test was undone; it is not a measured
  or fitted chair angle. No automatic photo-fitted lean is included here.

## Running the existing local demo

From the repository root, use `scripts/start-wue.ps1`; then open
`http://127.0.0.1:5174/`. Read-only readiness:
`scripts/start-wue.ps1 -CheckOnly`.

The launcher uses the already installed environment: worker on 8010, API on
8011, frontend on 5174, and the existing SAM 2.1 GPU setup in WSL. It does not
install dependencies, reset/migrate databases, or terminate conflicting apps.
Healthy services are reused, not automatically reloaded after source changes.
Startup from stopped WUE services can be checked separately; full laptop reboot
recovery is still unverified.

## Remaining work and defense limits

1. Resolve chair thickness and supported rear lean using measurements or
   independently marked member boundaries; label assumptions as provisional.
   Overlapping side silhouettes still overestimate slat depth. The supplied
   Top chair image is angled, not true overhead evidence.
2. Have the user review and correct the draft before finalization and its
   deterministic 3D/BOM/quote workflow. Preserve the working table demonstration.
3. Rehearse the defense path and freeze risky architecture/model-training changes.
4. Evaluate physical dimensions, shape similarity, usability, and processing time
   with documented test cases. Classification confidence is not accuracy.

SAM provides pretrained segmentation; semantic part extraction and geometric
estimation remain heuristic and user-assisted. Hidden construction, curved rail
depth, and exact stock thickness are not solved by straight profile extrusion.
No new training, dependencies, geometry schema, or quotation rules were added
in the rotation/branding checkpoint.
