# WUE prototype checkpoint — October 1, 2026

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
