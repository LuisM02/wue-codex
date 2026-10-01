# WUE prototype checkpoint — October 1, 2026

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

## Fresh verification

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
  is a draft with `parts_reviewed_at = null`. Approximate overall size:
  450 × 900 × 500 mm. Do not confirm or finalize on the user's behalf.
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
