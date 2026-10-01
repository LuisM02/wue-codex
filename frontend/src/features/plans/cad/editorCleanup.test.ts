import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PlanComponent } from "../../../types/api";
import { CanvasWorkspace } from "./CanvasWorkspace";
import { PartReviewGuide } from "./PartReviewGuide";
import { nearestProfilePoint } from "./editorGeometry";
import type { ReferenceImages } from "./referencePhotos";

const part = {
  id: "part", component_name: "tabletop", component_type: "panel", sort_order: 0,
  x: "0", y: "700", z: "0", width: "1800", height: "50", depth: "900",
  rotation_x: "0", rotation_y: "0", rotation_z: "0", geometry_kind: "extruded_profile",
  profile_points: [{ u: "0", v: "0" }, { u: "1800", v: "0" }, { u: "1800", v: "50" }, { u: "0", v: "50" }],
  source_views: ["front"],
} as PlanComponent;

function canvasMarkup(overrides: Partial<Parameters<typeof CanvasWorkspace>[0]> = {}) {
  return renderToStaticMarkup(createElement(CanvasWorkspace, {
    components: [part], dimensions: null, selectedId: "part", view: "front", locked: false,
    gridVisible: true, snapEnabled: true, referenceView: null, referenceOptions: [],
    photoVisible: false, zoom: 1, pan: { x: 0, y: 0 }, onPan() {}, onZoom() {}, onReference() {},
    onCalibration: async () => true, onSelect() {}, onPreview() {}, onCommit() {}, ...overrides,
  }));
}

describe("Uncluttered outline editing", () => {
  it("keeps outline dots and point-insertion controls hidden by default", () => {
    const before = JSON.stringify(part);
    const markup = canvasMarkup();
    expect(markup).toContain('aria-pressed="false">Edit outline</button>');
    expect(markup).not.toContain("cad-profile-handle");
    expect(markup).not.toContain("Add point");
    expect(markup).not.toContain("Remove selected");
    expect(markup).toContain("cad-resize-handle");
    expect(JSON.stringify(part)).toBe(before);
  });

  it("retains opt-in editing in Back but not unsupported or locked projections", () => {
    expect(canvasMarkup({ view: "back" })).toContain("Edit outline");
    for (const view of ["left", "right", "top"] as const) expect(canvasMarkup({ view })).not.toContain("Edit outline");
    expect(canvasMarkup({ locked: true })).not.toContain("Edit outline");
    expect(canvasMarkup({ components: [{ ...part, rotation_x: "10" }] })).not.toContain("Edit outline");
    expect(canvasMarkup({ selectedId: null })).not.toContain("Edit outline");
  });

  it("lets densely traced vertices be selected without reducing or adding points", () => {
    const dense = { ...part, profile_points: Array.from({ length: 42 }, (_, index) => ({ u: String(index), v: "0" })) };
    const before = JSON.stringify(dense);
    expect(nearestProfilePoint(dense, 25.1, 700)).toBe(25);
    expect(nearestProfilePoint(dense, -25.1, 700, -1)).toBe(25);
    expect(JSON.stringify(dense)).toBe(before);
  });
});

describe("Compact part review", () => {
  it("collapses detailed guidance while retaining part navigation and review safeguards", () => {
    const markup = renderToStaticMarkup(createElement(PartReviewGuide, {
      furnitureType: "dining_table", components: [part], selectedId: "part",
      referenceImages: { front: {}, back: {}, left: {}, right: {}, top: {} } as ReferenceImages,
      locked: false, busy: false, focusSelected: false, onSelect() {}, onCompare() {}, onFocus() {},
    }));
    expect(markup).toContain('class="cad-review-guide__details"><summary>Review help &amp; photo comparison</summary>');
    expect(markup).not.toContain('class="cad-review-guide__details" open');
    expect(markup).toContain("Previous part");
    expect(markup).toContain("Next part");
    expect(markup).toContain("Show only this part");
    expect(markup).toContain("Compare Back photo");
    expect(markup).toContain("confirmation does not finalize");
    expect(markup).toContain("not verified measurements");
  });
});
