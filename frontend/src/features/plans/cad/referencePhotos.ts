import type { ImageView } from "../../../types/api";
import type { OrthographicView } from "./editorGeometry";

export type ReferenceImageUrls = Partial<Record<ImageView, string>>;

export interface ReferenceOption {
  value: ImageView;
  label: string;
}

const VIEW_CANDIDATES: Record<OrthographicView, ImageView[]> = {
  front: ["front", "back"],
  side: ["left", "right"],
  top: ["top"],
};

export function referenceOptionsForView(
  view: OrthographicView,
  imageUrls: ReferenceImageUrls,
): ReferenceOption[] {
  return VIEW_CANDIDATES[view]
    .filter((candidate) => Boolean(imageUrls[candidate]))
    .map((candidate) => ({
      value: candidate,
      label: `${candidate[0].toUpperCase()}${candidate.slice(1)} photo`,
    }));
}

export function initialReferenceByView(
  imageUrls: ReferenceImageUrls,
): Record<OrthographicView, ImageView | null> {
  return {
    front: referenceOptionsForView("front", imageUrls)[0]?.value ?? null,
    side: referenceOptionsForView("side", imageUrls)[0]?.value ?? null,
    top: referenceOptionsForView("top", imageUrls)[0]?.value ?? null,
  };
}
