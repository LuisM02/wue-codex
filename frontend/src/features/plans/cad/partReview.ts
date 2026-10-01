import type { FurnitureType, ImageView, PlanComponent } from "../../../types/api";
import type { OrthographicView } from "./editorGeometry";
import { referenceOptionsForView, type ReferenceImages } from "./referencePhotos";

export function adjacentPartId(components: PlanComponent[], selectedId: string | null, direction: -1 | 1): string | null {
  if (!components.length) return null;
  const index = components.findIndex((part) => part.id === selectedId);
  if (index < 0) return direction === 1 ? components[0].id : null;
  return components[index + direction]?.id ?? null;
}

export function comparisonPhoto(view: OrthographicView, component: PlanComponent, images: ReferenceImages): ImageView | null {
  const available = referenceOptionsForView(view, images);
  // Prefer a recorded source, but another supplied photo can still be used for
  // manual comparison. It must not be relabeled as an AI source by doing so.
  return available.find((option) => component.source_views.includes(option.value))?.value
    ?? available[0]?.value ?? null;
}

export function partReviewChecks(type: FurnitureType, component: PlanComponent): string[] {
  const name = component.component_name;
  if (type === "bookshelf") {
    if (/^shelf_[1-9]\d*$/.test(name)) return [
      "Front: check this shelf's height, clear width and visible face thickness; count all photographed shelves.",
      "Side / Top: check depth and front/back placement. Front edges alone do not establish these dimensions.",
    ];
    if (name === "bottom_panel" || name === "top_panel") return [
      "Front: check the terminal panel's own face boundaries, width and position—not just the interior shelf thickness.",
      "Side: check depth, feet/overhang and how this panel meets the sides. Missing boundaries require manual correction.",
    ];
    if (name === "back_panel") return [
      "Back: check whether a full backing panel actually exists and whether its width/height match the frame.",
      "Side / Top: check backing thickness and rear position; these may be provisional, not photo-measured.",
    ];
    if (name === "left_side" || name === "right_side") return [
      "Front: check this side's height, face width and lower foot outline.",
      "Side: check panel depth and any cut-outs. A rectangular proposal may still need reshaping.",
    ];
  }
  return [
    "Front: compare the selected part's identity, outline, width, height and position with the matching photograph.",
    "Side / Top: check depth, front/back placement, tilt and overlap. Hidden construction still needs manual verification.",
  ];
}
