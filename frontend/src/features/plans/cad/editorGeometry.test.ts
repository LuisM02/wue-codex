import { describe, expect, it } from "vitest";

import type { PlanComponent } from "../../../types/api";
import { EditorHistory } from "./editorHistory";
import {
  canMutatePlan,
  edgeSnap,
  moveComponent,
  nextShelfName,
  projectComponent,
  resizeComponent,
  screenDeltaToWorld,
  snapToGrid,
} from "./editorGeometry";

const component: PlanComponent = {
  id: "part",
  plan_id: "plan",
  component_name: "seat",
  component_type: "panel",
  width: "450",
  height: "40",
  depth: "420",
  thickness: null,
  x: "25",
  y: "430",
  z: "30",
  rotation: "0",
  rotation_x: "0",
  rotation_y: "0",
  rotation_z: "0",
  geometry_kind: "box",
  profile_points: null,
  source_reconstruction_part_id: null,
  source_confidence: null,
  source_views: [],
  quantity: 1,
  sort_order: 0,
  created_at: "",
  updated_at: "",
};

describe("orthographic CAD geometry", () => {
  it("maps front, side, and top views without changing canonical axes", () => {
    expect(projectComponent(component, "front")).toEqual({ horizontal: 25, vertical: 430, width: 450, height: 40 });
    expect(projectComponent(component, "side")).toEqual({ horizontal: 30, vertical: 430, width: 420, height: 40 });
    expect(projectComponent(component, "top")).toEqual({ horizontal: 25, vertical: 30, width: 450, height: 420 });
    expect(projectComponent({ ...component, depth: null, thickness: "18" }, "side").width).toBe(18);
  });

  it("converts downward browser motion into decreasing world vertical position", () => {
    expect(screenDeltaToWorld(20, 30, 2)).toEqual({ horizontal: 10, vertical: -15 });
  });

  it("moves only the axes represented by each view", () => {
    const front = moveComponent(component, "front", 20, 10, 2, null);
    expect([front.x, front.y, front.z]).toEqual(["35", "425", "30"]);
    const side = moveComponent(component, "side", 20, 10, 2, null);
    expect([side.x, side.y, side.z]).toEqual(["25", "425", "40"]);
    const top = moveComponent(component, "top", 20, 10, 2, null);
    expect([top.x, top.y, top.z]).toEqual(["35", "430", "25"]);
  });

  it("snaps numeric coordinates to the grid", () => {
    expect(snapToGrid(124, 25)).toBe(125);
    expect(snapToGrid(-11, 25)).toBe(0);
  });

  it("snaps a nearby component edge and returns a visible guide", () => {
    const snapped = edgeSnap(
      { horizontal: 96, vertical: 12, width: 20, height: 20 },
      [{ horizontal: 50, vertical: 10, width: 50, height: 30 }],
      5,
    );
    expect(snapped.horizontal).toBe(100);
    expect(snapped.vertical).toBe(10);
    expect(snapped.guides).toEqual([
      { axis: "vertical", value: 100 },
      { axis: "horizontal", value: 10 },
    ]);
  });

  it("keeps resized geometry positive", () => {
    const unchanged = resizeComponent(component, "front", "south-east", -1000, 1000, 1, null);
    expect(unchanged).toEqual(component);
    const resized = resizeComponent(component, "side", "north-east", 40, -20, 2, null);
    expect(Number(resized.depth)).toBe(440);
    expect(Number(resized.height)).toBe(50);
  });

  it("chooses the next missing valid shelf number", () => {
    const shelves = [
      { ...component, component_name: "shelf_1" },
      { ...component, id: "2", component_name: "shelf_3" },
    ];
    expect(nextShelfName(shelves)).toBe("shelf_2");
  });

  it("locks mutation for finalized plans", () => {
    expect(canMutatePlan("draft")).toBe(true);
    expect(canMutatePlan("finalized")).toBe(false);
  });
});

describe("bounded editor history", () => {
  it("supports undo, redo, and clears redo after a new edit", () => {
    const history = new EditorHistory<number>(2);
    history.record({ before: 1, after: 2 });
    history.record({ before: 2, after: 3 });
    expect(history.undo()).toEqual({ before: 2, after: 3 });
    expect(history.canRedo).toBe(true);
    expect(history.redo()).toEqual({ before: 2, after: 3 });
    history.undo();
    history.record({ before: 2, after: 4 });
    expect(history.canRedo).toBe(false);
  });
});
