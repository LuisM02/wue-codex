# WUE local vision worker

This process is deliberately separate from the business API. It receives exactly five verified views, rejects duplicate or incoherent inputs, and returns photo-derived editable geometry.

The default pipeline is a lightweight baseline that runs immediately on Windows without downloading a model checkpoint. It traces the actual silhouettes, checks opposite-view consistency and expected orientation, identifies structural regions, and scales them to the user's measurements. It is most reliable when one furniture item is photographed against a plain contrasting background.

Version `0.3.0` contains a lazy SAM 2.1 adapter and photo-derived chair structural fitting. When deliberately configured, it prompts SAM with the centered furniture capture area instead of trusting a clutter-sensitive color outline, replaces the foreground mask with SAM's selected mask, and records the neural provider/checkpoint provenance in the existing response contract. Chair fitting separates the dense seat and backrest bands, persistent lower leg columns, visible backrest posts, and horizontal stretchers across the front and side silhouettes. It never silently downloads a checkpoint and never claims dense 3D reconstruction or trained semantic part recognition is loaded.

The dining-table fitter now samples the lower silhouette to separate four legs, identifies visible front/rear and side apron bands, and compensates for the front photo's projected tabletop thickness. When a neural box-prompt mask floods the open space beneath a table, the worker retains the clearer foreground silhouette for that view and reports the fallback. It also warns when supplied width/height proportions differ sharply from the photo. Apron depth, hidden joints, and exact slab thickness remain estimates requiring review.

Existing finalized designs can use **Rebuild from photos** in the plan editor to create a new draft from a fresh analysis. The previous finalized geometry is retained. This structural fitting is provisional: it is not a manufacturing cut list or a guarantee of the photographed furniture's exact construction, especially for upholstery, concealed joints, and occluded parts.

## Optional SAM 2.1 provider

Meta's official SAM 2 repository recommends Python 3.10 or newer, PyTorch 2.5.1 or newer, and WSL with Ubuntu for Windows GPU installations. Its code and checkpoints are Apache-2.0. The verified Windows development machine uses the isolated environment recorded in [AI_ENVIRONMENT.md](AI_ENVIRONMENT.md). Model files remain inside WSL and are never committed to Git.

Start the configured GPU worker from the repository root:

```powershell
.\scripts\start-sam2-worker.ps1
```

`GET /v1/model-status` reports whether the package and local checkpoint are available, whether CUDA will be used, and whether the checkpoint has actually loaded. An unavailable configured provider returns `503` during inference instead of falling back invisibly.

Official references: [SAM 2 repository](https://github.com/facebookresearch/sam2) and [installation guide](https://github.com/facebookresearch/sam2/blob/main/INSTALL.md).

To run the dependency-light Windows baseline instead, use:

```powershell
..\.venv\Scripts\python.exe -m uvicorn wue_worker.main:app --host 127.0.0.1 --port 8010
```

The service exposes `GET /health`, `GET /v1/model-status`, `POST /v1/classify`, and `POST /v1/reconstruct`.

### Table regression guardrails

Table apron proposals require a stable narrower silhouette band beneath the
tabletop. This avoids interpreting leftover slab pixels or rounded corners as
extra panels while retaining aprons with small overhangs. Side apron proposals
also require a band in the side view. Fully flush/hidden bands and concealed
joinery still need manual review. Controlled cases cover absent aprons, absent
side bands, small overhangs, and changed leg spacing; they are not accuracy
benchmarks. The September 30 suite has 18 passing tests.

For a read-only saved-photo inference probe, use the repository's existing
Windows virtual environment to run `scripts/probe-saved-furniture.py` with a
furniture UUID from the repository root. It sends photos to the local worker
directly and does not persist a new analysis or plan.

### October 1 chair and side-apron hardening

The mask guard also rejects a neural mask whose bounding envelope expands onto
floor/shadow around an open furniture silhouette, even when its fill ratio is
below 0.70. It reports the clearer-foreground fallback rather than hiding it.
Chair fitting retains every observed backrest column, names the outer posts and
middle `backrest_slat_N` parts separately, and uses the right-side image for
front-to-back placement. Mirror the left reference when comparing Side view.
Side table aprons no longer depend on detecting a front apron and use their own
observed vertical band. The latest worker suite has 23 passing tests.

A new user-supplied slatted-chair set produced 14 editable parts, including six
middle slats, in a separate unreviewed draft with approved approximate dimensions
450 × 900 × 500 mm. Seat/apron separation remains incomplete; backrest/slat
depths are silhouette envelopes, not verified stock thickness. Its angled Top
image cannot establish overhead dimensions. This test is workflow/shape evidence,
not a dimensional-accuracy benchmark or proof of generalization.

For new local photos, `scripts/probe-photo-set.py --front PATH --back PATH
--left PATH --right PATH --top PATH` is read-only by default. Add `--width`,
`--height`, `--depth` and explicit `--save-test-copy NAME` only to persist a
separate draft. It leaves `parts_reviewed_at` null and never finalizes a plan.

### Later seat/apron checkpoint — current worker result

`_chair_apron_band` follows a sustained narrower band below the seat's widest
lip, stops at leg-only space, and rejects tapered/rounded edges without sustained
evidence. Front, Back and Right apron evidence is independent; the right band
supports a provisional symmetric side pair. `_row_depth_estimate` uses median
contiguous row-span widths/centers rather than extruding a leaning member's full
swept envelope. It remains a straight-extrusion approximation, and overlapping
slats can still overestimate thickness; no camera-pose or neural part model is
added. Current suite: **30 passing tests**, including absent/rounded-seat apron
cases, independent evidence, changed apron height, leaning posts and changed
visible cross-section. Two existing dependency deprecations remain.

The separate live `Slatted chair seat-apron test (approx. size)` proposes 18 parts
and stays unreviewed: seat height 77.3438 mm (formerly 135.9375), front apron
58.5938 mm, rail depth 107.4561 mm, post/slat depth 100.8772 mm. These are still
projected estimates, not validated manufacturing dimensions. The earlier
14-part chair was finalized during user testing and is preserved. The new copy's
four elevation overlays have object-bound crops; Top remains angled/unadjusted.
The retained table still proposes nine parts in a read-only probe and its saved
plan is unchanged.
