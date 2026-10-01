import type { FurnitureType, PlanComponent } from "../../../types/api";
import { EDITOR_VIEWS, type OrthographicView } from "./editorGeometry";
import { adjacentPartId, comparisonPhoto, partReviewChecks } from "./partReview";
import type { ReferenceImages } from "./referencePhotos";

interface Props {
  furnitureType: FurnitureType;
  components: PlanComponent[];
  selectedId: string | null;
  referenceImages: ReferenceImages;
  locked: boolean;
  busy: boolean;
  focusSelected: boolean;
  onSelect: (id: string) => void;
  onCompare: (view: OrthographicView) => void;
  onFocus: () => void;
}

export function PartReviewGuide({ furnitureType, components, selectedId, referenceImages, locked, busy, focusSelected, onSelect, onCompare, onFocus }: Props) {
  const index = components.findIndex((part) => part.id === selectedId);
  const selected = components[index];
  const previous = adjacentPartId(components, selectedId, -1);
  const next = adjacentPartId(components, selectedId, 1);
  const views = EDITOR_VIEWS;
  return (
    <section className="cad-review-guide" aria-label="Part-by-part inspection guide">
      <div className="cad-review-guide__heading">
        <div aria-live="polite">
          <small>{locked ? "Read-only inspection" : "Part-by-part review"}</small>
          <strong>{selected ? `Part ${index + 1} of ${components.length}: ${selected.component_name.replaceAll("_", " ")}` : "Select a part to compare"}</strong>
        </div>
        <div className="cad-review-guide__actions">
          <button type="button" disabled={busy || !previous} onClick={() => previous && onSelect(previous)}>Previous part</button>
          <button type="button" disabled={busy || !next} onClick={() => next && onSelect(next)}>Next part</button>
          <button type="button" aria-pressed={focusSelected} disabled={busy || !selected} onClick={onFocus}>Show only this part</button>
        </div>
      </div>
      <details className="cad-review-guide__details">
        <summary>Review help &amp; photo comparison</summary>
      {selected && (
        <>
          <p className="cad-review-guide__size">Current local size: {Number(selected.width).toFixed(1)} × {Number(selected.height).toFixed(1)} × {selected.depth !== null ? Number(selected.depth).toFixed(1) : "—"} mm (X × Y × Z). These are editable model values, not verified measurements.</p>
          <div className="cad-review-guide__actions" role="group" aria-label="Compare selected part with photos">
            {views.map((view) => (
              <button key={view} type="button" disabled={busy || !comparisonPhoto(view, selected, referenceImages)} onClick={() => onCompare(view)}>
                Compare {view[0].toUpperCase() + view.slice(1)} photo
              </button>
            ))}
          </div>
          <details>
            <summary>What to check for this part</summary>
            <ul>{partReviewChecks(furnitureType, selected).map((check) => <li key={check}>{check}</li>)}</ul>
            <p>Recorded photo sources: {selected.source_views.length ? selected.source_views.join(" · ") : "none—manually added or legacy part"}. A comparison photo is not proof that its dimensions were fitted from that view.</p>
          </details>
        </>
      )}
      <p className="cad-review-guide__footnote">Navigation and isolation do not record a review. {locked ? "This finalized geometry cannot be edited." : "Review all parts before using Confirm parts; confirmation does not finalize the drawing."} Photo alignment is not camera calibration.</p>
      </details>
    </section>
  );
}
