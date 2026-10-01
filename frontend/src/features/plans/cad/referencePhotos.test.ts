import { describe, expect, it } from "vitest";

import { initialReferenceByView, referenceOptionsForView } from "./referencePhotos";
import { calibrationPayload } from "./CanvasWorkspace";

describe("orthographic reference photographs", () => {
  const imageUrls = {
    front: "/front",
    back: "/back",
    left: "/left",
    right: "/right",
    top: "/top",
  } as const;

  it("offers only photographs that correspond to the active projection", () => {
    expect(referenceOptionsForView("front", imageUrls).map((item) => item.value)).toEqual(["front"]);
    expect(referenceOptionsForView("back", imageUrls).map((item) => item.value)).toEqual(["back"]);
    expect(referenceOptionsForView("left", imageUrls).map((item) => item.value)).toEqual(["left"]);
    expect(referenceOptionsForView("right", imageUrls).map((item) => item.value)).toEqual(["right"]);
    expect(referenceOptionsForView("side", imageUrls).map((item) => item.value)).toEqual(["left", "right"]);
    expect(referenceOptionsForView("top", imageUrls).map((item) => item.value)).toEqual(["top"]);
  });

  it("chooses the first available source without inventing a missing photo", () => {
    expect(initialReferenceByView({ back: "/back", right: "/right" })).toEqual({
      front: null,
      back: "back",
      left: null,
      right: "right",
      side: "right",
      top: null,
    });
  });

  it("never substitutes the opposite photograph for a named view", () => {
    expect(referenceOptionsForView("front", { back: "/back" })).toEqual([]);
    expect(referenceOptionsForView("left", { right: "/right" })).toEqual([]);
    expect(referenceOptionsForView("back", { front: "/front" })).toEqual([]);
    expect(referenceOptionsForView("right", { left: "/left" })).toEqual([]);
  });

  it("converts visible photo margins into a normalized object crop", () => {
    expect(calibrationPayload({ left: 10, right: 15, top: 5, bottom: 20, isMirrored: true })).toEqual({
      object_left_ratio: "0.100000",
      object_top_ratio: "0.050000",
      object_width_ratio: "0.750000",
      object_height_ratio: "0.750000",
      is_mirrored: true,
    });
    expect(calibrationPayload({ left: 60, right: 40, top: 0, bottom: 0, isMirrored: false })).toBeNull();
  });
});
