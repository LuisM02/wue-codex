import { Notice } from "../../components/Feedback";
import type { FurnitureDimensions, FurniturePlan, FurnitureReconstruction } from "../../types/api";
import { analysisMatchesPlan } from "./analysisProvenance";

function reviewNote(warning: string): string {
  if (warning.startsWith("SAM 2.1 segments")) {
    return "AI identifies the visible outline. Hidden depth and individual part identities still require review.";
  }
  const correctedView = warning.match(/neural mask filled open space in the (\w+) view/);
  if (correctedView) {
    return `The ${correctedView[1]} outline was corrected because the AI included empty space beneath the furniture.`;
  }
  return warning;
}

export function ReconstructionFeedback({
  analysis,
  dimensions,
  plan,
}: {
  analysis: FurnitureReconstruction;
  dimensions: FurnitureDimensions | null;
  plan: FurniturePlan | null;
}) {
  const dimensionWarning = analysis.warnings.find((warning) =>
    warning.includes("width and height strongly disagree"),
  );
  const notes = [...new Set(analysis.warnings.filter((warning) => warning !== dimensionWarning).map(reviewNote))];

  return (
    <aside className="analysis-feedback" aria-label="Photo analysis review notes">
      <div className="analysis-feedback__summary">
        <strong>Latest photo analysis · {analysis.parts.length} proposed parts</strong>
        {dimensions && (
          <span>
            Supplied overall size: {Number(dimensions.width_mm)} × {Number(dimensions.height_mm)} × {Number(dimensions.depth_mm)} mm
            {" "}(width × height × depth)
          </span>
        )}
      </div>
      {!analysisMatchesPlan(analysis, plan) && (
        <Notice tone="warning">
          <strong>Latest analysis is separate from this revision.</strong>{" "}
          Its proposed parts no longer match this drawing's source parts. These notes describe the latest photo proposal,
          not this saved drawing. Your saved geometry has not been replaced.
        </Notice>
      )}
      {dimensionWarning && (
        <Notice tone="warning">
          <strong>Check the overall measurements.</strong>{" "}
          The width and height do not match the proportions in the front photo. Correct the scale before accepting this design.
        </Notice>
      )}
      {notes.length > 0 && (
        <details>
          <summary>What needs checking in this proposal ({notes.length})</summary>
          <ul>{notes.map((note) => <li key={note}>{note}</li>)}</ul>
        </details>
      )}
    </aside>
  );
}
