import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PlanComponent } from "../../../types/api";
import { adjacentPartId, comparisonPhoto, partReviewChecks } from "./partReview";
import { PartReviewGuide } from "./PartReviewGuide";
import { CanvasWorkspace } from "./CanvasWorkspace";
import { PropertiesPanel } from "./PropertiesPanel";
import type { ReferenceImages } from "./referencePhotos";

const shelf = {
  id: "shelf", component_name: "shelf_1", component_type: "panel", sort_order: 0,
  width: "400", height: "18", depth: "300", x: "20", y: "400", z: "0",
  rotation_x: "0", rotation_y: "0", rotation_z: "0", geometry_kind: "box",
  profile_points: null, source_views: ["front"], source_confidence: "0.5",
} as PlanComponent;
const bottom = { ...shelf, id: "bottom", component_name: "bottom_panel", y: "20", sort_order: 1 };
const components = [shelf, bottom];
const photos = { front: {}, back: {}, right: {}, top: {} } as ReferenceImages;

describe("Part-by-part inspection helpers", () => {
  it("navigates without wrapping or mutating geometry", () => {
    const before = JSON.stringify(components);
    expect(adjacentPartId(components, "shelf", 1)).toBe("bottom");
    expect(adjacentPartId(components, "bottom", -1)).toBe("shelf");
    expect(adjacentPartId(components, "shelf", -1)).toBeNull();
    expect(adjacentPartId(components, "bottom", 1)).toBeNull();
    expect(JSON.stringify(components)).toBe(before);
  });
  it("starts at the first part after deselection, and handles empty/deleted selections", () => {
    expect(adjacentPartId(components, null, 1)).toBe("shelf");
    expect(adjacentPartId(components, "deleted", 1)).toBe("shelf");
    expect(adjacentPartId(components, null, -1)).toBeNull();
    expect(adjacentPartId([], null, 1)).toBeNull();
  });
  it("prefers a recorded source when its comparison photo exists", () => {
    expect(comparisonPhoto("front", { ...shelf, source_views: ["back"] }, photos)).toBe("back");
    expect(comparisonPhoto("side", shelf, photos)).toBe("right");
    expect(shelf.source_views).toEqual(["front"]);
  });
  it("never selects a missing or incompatible photo", () => {
    expect(comparisonPhoto("front", shelf, { right: photos.right })).toBeNull();
    expect(comparisonPhoto("top", shelf, { front: photos.front })).toBeNull();
  });
  it.each(["shelf_1", "shelf_12"])("gives %s shelf checks without claiming measured depth", (name) => {
    const checks = partReviewChecks("bookshelf", { ...shelf, component_name: name }).join(" ");
    expect(checks).toContain("count all photographed shelves");
    expect(checks).toContain("Front edges alone do not establish");
  });
  it.each(["top_panel", "bottom_panel"])("gives independent terminal face checks for %s", (name) => {
    expect(partReviewChecks("bookshelf", { ...shelf, component_name: name }).join(" ")).toContain("own face boundaries");
  });
  it("does not assume a full backing exists", () => {
    expect(partReviewChecks("bookshelf", { ...shelf, component_name: "back_panel" }).join(" ")).toContain("whether a full backing panel actually exists");
  });
  it.each(["left_side", "right_side"])("requires outline/cut-out checks for %s", (name) => {
    expect(partReviewChecks("bookshelf", { ...shelf, component_name: name }).join(" ")).toContain("may still need reshaping");
  });
  it("uses generic checks for renamed parts and other furniture types", () => {
    expect(partReviewChecks("bookshelf", { ...shelf, component_name: "renamed" })[0]).toContain("identity");
    expect(partReviewChecks("chair", shelf)[1]).toContain("tilt and overlap");
    expect(partReviewChecks("dining_table", shelf)[1]).toContain("manual verification");
  });
});

function guideMarkup(overrides: Partial<Parameters<typeof PartReviewGuide>[0]> = {}) {
  return renderToStaticMarkup(createElement(PartReviewGuide, {
    furnitureType: "bookshelf", components, selectedId: "shelf", referenceImages: photos,
    locked: false, busy: false, focusSelected: false,
    onSelect() {}, onCompare() {}, onFocus() {}, ...overrides,
  }));
}

describe("Inspection guide rendering", () => {
  it("shows selection position, size and the review/accuracy distinction", () => {
    const markup = guideMarkup();
    expect(markup).toContain("Part 1 of 2: shelf 1");
    expect(markup).toContain("400.0 × 18.0 × 300.0 mm");
    expect(markup).toContain("not verified measurements");
    expect(markup).toContain("Navigation and isolation do not record a review");
    expect(markup).not.toContain("50%");
  });
  it("keeps source metadata separate from manual comparison", () => {
    const markup = guideMarkup({ components: [{ ...shelf, source_views: [] }] });
    expect(markup).toContain("none—manually added or legacy part");
    expect(markup).toContain("not proof that its dimensions were fitted");
  });
  it("handles deselection and missing depth without a made-up size", () => {
    expect(guideMarkup({ selectedId: null })).toContain("Select a part to compare");
    expect(guideMarkup({ components: [{ ...shelf, depth: null }] })).toContain("× — mm");
  });
  it("keeps finalized inspection read-only and provides no confirm action", () => {
    const markup = guideMarkup({ locked: true });
    expect(markup).toContain("This finalized geometry cannot be edited");
    expect(markup).not.toContain("using Confirm parts");
    expect(markup).not.toContain("onPersist");
  });
  it("labels proposal confidence as distinct from reconstruction accuracy, including zero", () => {
    const markup = renderToStaticMarkup(createElement(PropertiesPanel, {
      component: { ...shelf, source_confidence: "0" }, locked: true, busy: false, onCommit() {},
    }));
    expect(markup).toContain("0% proposal confidence · not reconstruction accuracy");
  });
  it("does not invent confidence when metadata is absent", () => {
    const markup = renderToStaticMarkup(createElement(PropertiesPanel, {
      component: { ...shelf, source_confidence: null }, locked: false, busy: false, onCommit() {},
    }));
    expect(markup).not.toContain("proposal confidence");
  });
});

function canvasMarkup(focusSelected: boolean, selectedId: string | null = "shelf") {
  return renderToStaticMarkup(createElement(CanvasWorkspace, {
    components, dimensions: null, selectedId, view: "front", locked: true,
    gridVisible: true, snapEnabled: true, referenceView: null, referenceOptions: [],
    photoVisible: false, focusSelected, zoom: 1, pan: { x: 0, y: 0 },
    onPan() {}, onZoom() {}, onReference() {}, onCalibration: async () => true,
    onSelect() {}, onPreview() {}, onCommit() {},
  }));
}

describe("Selected-part isolation is display only", () => {
  it("hides other rendered shapes but keeps the selected part's scale and all saved parts", () => {
    const before = JSON.stringify(components);
    const full = canvasMarkup(false);
    const isolated = canvasMarkup(true);
    expect(full).toContain('aria-label="Select bottom panel"');
    expect(isolated).not.toContain('aria-label="Select bottom panel"');
    expect(isolated).toContain('aria-label="Select shelf 1"');
    expect(isolated).toContain("other parts are retained");
    const selectedRect = (markup: string) => markup.slice(markup.indexOf('aria-label="Select shelf 1"'))
      .match(/<rect x="[^"]+" y="[^"]+" width="[^"]+" height="[^"]+" rx="1.5"/)?.[0];
    expect(selectedRect(full)).toBeDefined();
    expect(selectedRect(full)).toBe(selectedRect(isolated));
    expect(JSON.stringify(components)).toBe(before);
  });
  it("shows all shapes again when there is no selected part", () => {
    expect(canvasMarkup(true, null)).toContain('aria-label="Select bottom panel"');
  });
});
