import type { FurnitureImage, ImageView } from "../../../types/api";
import type { OrthographicView } from "./editorGeometry";

export interface ReferenceImage {
  image: FurnitureImage;
  url: string;
}

export type ReferenceImages = Partial<Record<ImageView, ReferenceImage>>;
type ReferencePresence = Partial<Record<ImageView, unknown>>;

export interface ReferenceOption {
  value: ImageView;
  label: string;
}

const VIEW_CANDIDATES: Record<OrthographicView, ImageView[]> = {
  front: ["front"],
  back: ["back"],
  left: ["left"],
  right: ["right"],
  side: ["left", "right"],
  top: ["top"],
};

export function referenceOptionsForView(
  view: OrthographicView,
  images: ReferencePresence,
): ReferenceOption[] {
  return VIEW_CANDIDATES[view]
    .filter((candidate) => Boolean(images[candidate]))
    .map((candidate) => ({
      value: candidate,
      label: `${candidate[0].toUpperCase()}${candidate.slice(1)} photo`,
    }));
}

export function initialReferenceByView(
  images: ReferencePresence,
): Record<OrthographicView, ImageView | null> {
  return {
    front: referenceOptionsForView("front", images)[0]?.value ?? null,
    back: referenceOptionsForView("back", images)[0]?.value ?? null,
    left: referenceOptionsForView("left", images)[0]?.value ?? null,
    right: referenceOptionsForView("right", images)[0]?.value ?? null,
    side: referenceOptionsForView("side", images)[0]?.value ?? null,
    top: referenceOptionsForView("top", images)[0]?.value ?? null,
  };
}
