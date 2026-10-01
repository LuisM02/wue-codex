# Table mapping checkpoint — October 2, 2026

## Implemented

- `reconstruction-worker/wue_worker/geometry.py`: `_dining_table` detects
  `side_top_start` / `side_top_stop` using the side's own `_strongest_band`.
  Previously both boundaries were copied from normalized front-view rows.
  Side support sampling, slab-depth sampling and side-apron vertical mapping
  now use the side boundary. Visible side-apron evidence remains mandatory.
- `reconstruction-worker/wue_worker/imaging.py`: `validate_view_set` retains
  the fourfold rejection and 2.1-fold warning thresholds. A severe mismatch
  now reports photo proportions inconsistent with entered dimensions and asks
  the user to check dimensions, the named view and camera angle. Aspect ratios
  alone cannot establish that the photo orientation is wrong.
- `reconstruction-worker/wue_worker/__init__.py`: worker version `0.3.1`.
  `segmentation.py` and the reconstruction default use the central version,
  so future proposals are distinguishable from earlier `0.3.0` results.
  The SAM checkpoint and classifier structure gate are unchanged.
- `reconstruction-worker/tests/test_worker_api.py`: four regression cases
  cover independent side mapping, rejection wording/recovery, and unchanged
  warning/rejection thresholds. Existing health/proposal tests verify `0.3.1`.

No frontend changes, dependencies, database migrations, API schema changes,
material-price changes or finalized-source-of-truth changes were made.

## Verification

- Final full worker suite: **66 passed**.
- Backend HTTP reconstruction adapter suite: **15 passed**.
- Full backend/frontend/build not rerun: last verified totals are 381 backend
  and 115 frontend; production build passed with a large lazy viewer-chunk warning.
- Worker safely reloaded on port 8010; health reports `0.3.1`, local SAM 2.1
  CUDA provider ready. API 8011 and frontend 5174 were not restarted.
- Live inference used the saved photographs from furniture
  `730399e2-b6bf-4a70-82ff-49e3501508e6`, via business API GETs and direct worker
  `POST /v1/reconstruct`. No business API write endpoints were called.
- Approximate dimensions 450 × 900 × 500 mm still returned 422, now with the
  truthful proportion-mismatch explanation.
- Approximate dimensions 1800 × 750 × 900 mm returned nine parts using
  `0.3.1/sam2.1_hiera_base_plus/sha256:a2345aede8715ab1`.
  Tabletop underside Y remained 701.25 mm. The proposed side-apron Y changed
  from 606.1055 to 651.9730 mm and height from 77.5251 to 49.2770 mm;
  their modeled top now coincides with that underside (rounded gap 0 mm,
  previously 17.6194 mm). This was a **proposal only**, not a saved replacement.
- Saved table plan list was equal immediately before and after the probe.
  All protected retained design/calibration and sample quote responses matched
  their October 2 audit hashes.

## Concurrent draft edits preserved

A final comparison against the earlier audit showed only the draft's
`left_apron.y` and `right_apron.y` moved from `606.1055` to `623.7250`, plus
associated update timestamps (04:10:09 / 04:10:17 +08:00). These changes were
not produced by the read-only probe and were not reverted. Their retained
height is still 77.5251 mm; they are not the newly generated proposal above.
No components were added/deleted, and no review or finalization was recorded
by this revision. The historical audit snapshot must not be overwritten merely
to make its comparison pass.

## Limits and next step

The improvement addresses inconsistent per-view coordinate mapping on this
photo set, not validated dimensional accuracy, guaranteed reconstruction of
arbitrary furniture, or a new learned part detector. Slab thickness, hidden
stock depth, joinery and correspondence remain provisional.

Next: review the actual draft's visible parts against all five photographs,
correct any remaining geometry deliberately, then record review and finalize
only after approval. Inspect the derived 3D, BOM and sample-price quotation for
the defense. Do not regenerate over protected finalized designs or use demo
sizes/prices as measured or supplier-verified evidence.
