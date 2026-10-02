# Quotation disclosure checkpoint — October 2, 2026

## Problem addressed / IMPLEMENTED

Previously the working quote labeled its number "Exact total" and the page
"Build the final estimate". The existing limitations footnotes were inside
the builder, which print CSS hides. Saved cards carried snapshot costs and a
sample-price footer, but not net-volume, scope or construction caveats.
Printing could therefore omit important limitations.

This revision adds `QuoteLimitations.tsx`, a display-only shared scope note
outside the print-hidden builder and inside each saved quotation card.
`QuotationCard.tsx` renders wood quantity/unit/rate, screw quantity/rate and
assumed labor hours/rate directly from that quotation's immutable API fields.
It does not fetch current prices or change a saved record.

Working/saved totals are labeled **Calculated subtotal**; the page/header says
**prototype estimate**. The amount and backend endpoint names are unchanged.
The dedicated note discloses wood-only costing, net modeled volume excluding
cutting waste/stock layout, prototype hardware/labor assumptions, and excluded
tax, markup, overhead and currency. For a dining-table record, it explicitly
states that separate apron joints/fasteners/labor are not itemized. Correct
arithmetic does not validate physical dimensions, manufacturing accuracy or
structural safety. Real-priced records retain the same scope warning; DEMO
wood/labor names additionally retain the demonstration-price footer.

Print CSS keeps the dedicated note visible in a single-column quotation list,
with readable black assumption text. These notes are current UI guidance,
not newly persisted immutable quotation fields or supplier approval.

## Exact implementation files

- `frontend/src/features/estimates/EstimatePanel.tsx`
- `frontend/src/features/estimates/QuoteLimitations.tsx` (new)
- `frontend/src/features/estimates/QuotationCard.tsx` (new)
- `frontend/src/features/estimates/estimateDisclosures.test.ts` (new)
- `frontend/src/styles.css`
- `README.md`
- `docs/QUOTE_DISCLOSURE_CHECKPOINT_2026-10-02.md` (this document)

No dependencies, migrations, endpoints, calculator rules or catalog values
were added/changed. The finalization/review gates are unchanged.

## Verification

- Fresh frontend suite: **123 passed /15 files**, including eight disclosure
  cases covering all three types, pre-calculation visibility, saved snapshot
  input display/nonmutation, real-vs-demo prices, per-record type and print CSS.
- TypeScript/production build: passes. Existing lazy viewer chunk852.86kB
  warning remains. Test-only Node filesystem reading uses the existing Vitest
  runner; no new Node types/dependencies were installed.
- An initial test import needed adaptation to existing TypeScript types;
  a raw CSS test import returned empty under Vitest. Both were corrected;
  final tests/build pass. These were verification issues, not saved-data loss.
- Existing live **Dining → Table prototype demo (approx. size)** loaded,
  navigated through BOM to Quote, and recalculated using the same sample rates.
  Both working and saved subtotal still display **5,831.51**. Saved card shows
  53.36board ft ×100, 8pieces ×2 and3.2 assumed hours ×150 at display precision.
- Browser-rendered saved-card scope note is visible; delivered print stylesheet
  contains the visibility and single-column rules. No warn/error console logs
  appeared. **No physical printing, print-preview or PDF output was tested.**
- Read-only saved-demo checker passes before/after; standalone checker suite
  remains17 passing. Checked records remain unchanged, including the unreviewed
  audit draft. No quotation was created and no plan was reviewed/finalized.
- Full backend/worker suites were not rerun for this frontend-only revision;
  preceding verified totals are381/66. No physical-accuracy evaluation occurred.

## Remaining scope / defense freeze

This fixes an estimate-disclosure gap, not missing joinery detection, actual
stock purchase quantities, real-price/time validation, material classification,
authentication/RBAC, manufacturing safety or reconstruction accuracy.
Wood-only is an estimation scope, not a claim that AI identifies plastic or
upholstery. Preserve saved designs, price snapshots and user draft position edits.

User review of the pending draft and a recorded full rehearsal remain next.
Existing source ZIP packages identify their own commit; do not relabel an older
ZIP as containing this revision. No paper was created or uploaded by this change.
