import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { PlanComponent } from "../../../types/api";
import { componentDrawing, projectPoint } from "../../../lib/componentPose";
import { CanvasWorkspace } from "./CanvasWorkspace";
import { EditorToolbar } from "./EditorToolbar";
import { PartReviewGuide } from "./PartReviewGuide";
import { applyProjectedPosition, EDITOR_VIEWS, moveComponent, moveProfilePoint, projectComponent, resizeComponent, VIEW_DEFINITIONS } from "./editorGeometry";
import { initialReferenceByView, type ReferenceImages } from "./referencePhotos";

const part: PlanComponent = {
  id: "part", plan_id: "plan", component_name: "seat", component_type: "panel",
  width: "450", height: "40", depth: "420", thickness: null,
  x: "25", y: "430", z: "30", rotation: "0", rotation_x: "0", rotation_y: "0", rotation_z: "0",
  geometry_kind: "extruded_profile",
  profile_points: [{ u: "0", v: "0" }, { u: "450", v: "0" }, { u: "350", v: "40" }, { u: "0", v: "40" }],
  source_reconstruction_part_id: null, source_confidence: null, source_views: ["front"],
  quantity: 1, sort_order: 0, created_at: "", updated_at: "",
};

describe("Five directional views of one canonical model", () => {
  it("uses opposing directions without changing the saved geometry", () => {
    const before = JSON.stringify(part);
    expect(projectPoint({ x: 25, y: 430, z: 30 }, "back")).toEqual({ horizontal: -25, vertical: 430 });
    expect(projectPoint({ x: 25, y: 430, z: 30 }, "left")).toEqual({ horizontal: -30, vertical: 430 });
    expect(projectComponent(part, "back")).toEqual({ horizontal: -475, vertical: 430, width: 450, height: 40 });
    expect(projectComponent(part, "left")).toEqual({ horizontal: -450, vertical: 430, width: 420, height: 40 });
    expect(projectComponent(part, "right")).toEqual(projectComponent(part, "side"));
    expect(JSON.stringify(part)).toBe(before);
  });

  it.each(["back", "left"] as const)("moves to the right on screen in the %s view", (view) => {
    const moved = moveComponent(part, view, 20, 10, 2, null);
    const before = projectComponent(part, view), after = projectComponent(moved, view);
    expect(after.horizontal).toBe(before.horizontal + 10);
    expect(after.vertical).toBe(before.vertical - 5);
    expect(moved[VIEW_DEFINITIONS[view].horizontalPosition]).toBe(view === "back" ? "15" : "20");
    expect(view === "back" ? moved.z : moved.x).toBe(view === "back" ? part.z : part.x);
  });

  it.each(["back", "left"] as const)("translates rotated projected bounds when snapping in %s", (view) => {
    const rotated = { ...part, rotation_x: "15", rotation_y: "20" };
    const before = projectComponent(rotated, view);
    const moved = applyProjectedPosition(rotated, view, before.horizontal + 10, before.vertical - 5);
    const after = projectComponent(moved, view);
    expect(after.horizontal).toBeCloseTo(before.horizontal + 10);
    expect(after.vertical).toBeCloseTo(before.vertical - 5);
    expect(moved.rotation_y).toBe("20");
    expect(moved.profile_points).toEqual(rotated.profile_points);
    expect(resizeComponent(rotated, view, "north-east", 20, -10, 2, null)).toEqual(rotated);
  });

  it.each(["back", "left"] as const)("keeps the opposite screen edge fixed when resizing in %s", (view) => {
    const before = projectComponent(part, view);
    const east = resizeComponent(part, view, "north-east", 20, 0, 2, null);
    const west = resizeComponent(part, view, "north-west", 20, 0, 2, null);
    expect(projectComponent(east, view).horizontal).toBe(before.horizontal);
    expect(projectComponent(east, view).width).toBe(before.width + 10);
    expect(projectComponent(west, view).horizontal + projectComponent(west, view).width).toBe(before.horizontal + before.width);
    expect(projectComponent(west, view).width).toBe(before.width - 10);
    expect(Number(east[VIEW_DEFINITIONS[view].horizontalPosition])).toBe(Number(part[VIEW_DEFINITIONS[view].horizontalPosition]) - 10);
    expect(west[VIEW_DEFINITIONS[view].horizontalPosition]).toBe(part[VIEW_DEFINITIONS[view].horizontalPosition]);
  });

  it("edits a mirrored back outline point in canonical coordinates", () => {
    const moved = moveProfilePoint(part, 2, 20, 0, 2, null, -1);
    expect(moved.profile_points?.[2]).toEqual({ u: "340", v: "40" });
    expect(part.profile_points?.[2]).toEqual({ u: "350", v: "40" });
  });

  it.each(EDITOR_VIEWS)("draws a rotated part's visible faces in %s", (view) => {
    const drawing = componentDrawing({ ...part, rotation_x: "15", rotation_y: "20", rotation_z: "10" }, view);
    expect(drawing.faces.length).toBeGreaterThan(0);
    expect(drawing.edges.length).toBeGreaterThan(0);
    const axis = view === "left" || view === "right" ? "z" : "x";
    const opposite = view === "back" || view === "left";
    const mirrored = projectComponent({ ...part, rotation_x: "15", rotation_y: "20" }, view);
    const positive = projectComponent({ ...part, rotation_x: "15", rotation_y: "20" }, axis === "z" ? "right" : view === "top" ? "top" : "front");
    expect(mirrored.horizontal).toBeCloseTo(opposite ? -positive.horizontal - positive.width : positive.horizontal);
  });
});

describe("Clearly labeled directional navigation", () => {
  it("shows five selectable named views even when the plan is locked", () => {
    const markup = renderToStaticMarkup(createElement(EditorToolbar, {
      view: "back", gridVisible: true, snapEnabled: true, photoVisible: false, hasPhoto: false,
      locked: true, reviewMode: false, busy: false, canUndo: false, canRedo: false, zoom: 1,
      onView() {}, onGrid() {}, onSnap() {}, onPhoto() {}, onUndo() {}, onRedo() {},
      onZoomIn() {}, onZoomOut() {}, onFit() {}, onFinish() {},
    }));
    for (const view of EDITOR_VIEWS) expect(markup).toContain(`title="Show ${view} orthographic view"`);
    expect(markup).not.toContain("Show side orthographic view");
    expect(markup).toMatch(/title="Show back orthographic view" aria-pressed="true"/);
    expect(markup).toContain("Finalized / locked");
  });

  it("offers five explicit comparison buttons without approving the design", () => {
    const photos = { front: {}, back: {}, left: {}, right: {}, top: {} } as ReferenceImages;
    const markup = renderToStaticMarkup(createElement(PartReviewGuide, {
      furnitureType: "chair", components: [part], selectedId: "part", referenceImages: photos,
      locked: false, busy: false, focusSelected: false, onSelect() {}, onCompare() {}, onFocus() {},
    }));
    for (const view of EDITOR_VIEWS) expect(markup).toContain(`Compare ${view[0].toUpperCase() + view.slice(1)} photo`);
    expect(markup).toContain("Navigation and isolation do not record a review");
  });

  it.each(EDITOR_VIEWS)("labels the workspace and uses the matching %s photograph", (view) => {
    const photos = Object.fromEntries(EDITOR_VIEWS.map((name) => [name, {
      image: { id: name, updated_at: "", object_left_ratio: "0", object_top_ratio: "0",
        object_width_ratio: "1", object_height_ratio: "1", is_mirrored: false }, url: `/${name}.png`,
    }])) as ReferenceImages;
    const referenceView = initialReferenceByView(photos)[view];
    const markup = renderToStaticMarkup(createElement(CanvasWorkspace, {
      components: [part], dimensions: null, selectedId: "part", view, locked: true,
      gridVisible: true, snapEnabled: true, referenceImage: photos[view], referenceView, referenceOptions: [],
      photoVisible: true, zoom: 1, pan: { x: 0, y: 0 }, onPan() {}, onZoom() {}, onReference() {},
      onCalibration: async () => true, onSelect() {}, onPreview() {}, onCommit() {},
    }));
    expect(markup).toContain(`aria-label="${view} orthographic furniture drawing"`);
    expect(markup).toContain(`href="/${view}.png"`);
    expect(markup).toContain(`${view.toUpperCase()} VIEW`);
    expect(markup).not.toContain("cad-resize-handle");
    expect(markup).not.toContain("cad-profile-handle");
  });
});
