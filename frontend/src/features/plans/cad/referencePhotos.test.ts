import { describe, expect, it } from "vitest";

import { initialReferenceByView, referenceOptionsForView } from "./referencePhotos";

describe("orthographic reference photographs", () => {
  const imageUrls = {
    front: "/front",
    back: "/back",
    left: "/left",
    right: "/right",
    top: "/top",
  } as const;

  it("offers only photographs that correspond to the active projection", () => {
    expect(referenceOptionsForView("front", imageUrls).map((item) => item.value)).toEqual(["front", "back"]);
    expect(referenceOptionsForView("side", imageUrls).map((item) => item.value)).toEqual(["left", "right"]);
    expect(referenceOptionsForView("top", imageUrls).map((item) => item.value)).toEqual(["top"]);
  });

  it("chooses the first available source without inventing a missing photo", () => {
    expect(initialReferenceByView({ back: "/back", right: "/right" })).toEqual({
      front: "back",
      side: "right",
      top: null,
    });
  });
});
