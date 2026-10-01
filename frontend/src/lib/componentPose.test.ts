import { Box3, Euler, Vector3 } from "three";
import { describe, expect, it } from "vitest";

import { buildCenteredProfileGeometry } from "../features/viewer/profileGeometry";
import { applyProjectedPosition, moveProfilePoint, projectComponent, resizeComponent } from "../features/plans/cad/editorGeometry";
import type { PlanComponent } from "../types/api";
import { componentDrawing, componentVertices, hasComponentRotation, rotatePoint } from "./componentPose";

const part: PlanComponent = {
  id: "pose-test", plan_id: "test", component_name: "backrest_slat_1", component_type: "panel",
  width: "70", height: "300", depth: "20", thickness: null,
  x: "25", y: "450", z: "350", rotation: "0", rotation_x: "0", rotation_y: "0", rotation_z: "0",
  geometry_kind: "extruded_profile",
  profile_points: [{ u: "0", v: "0" }, { u: "70", v: "0" }, { u: "45", v: "300" }, { u: "0", v: "250" }],
  source_reconstruction_part_id: null, source_confidence: null, source_views: [], quantity: 1,
  sort_order: 0, created_at: "", updated_at: "",
};

function expectPoint(actual: { x: number; y: number; z: number }, expected: { x: number; y: number; z: number }) {
  expect(actual.x).toBeCloseTo(expected.x, 7);
  expect(actual.y).toBeCloseTo(expected.y, 7);
  expect(actual.z).toBeCloseTo(expected.z, 7);
}

describe("shared center-pivot pose", () => {
  it.each([[20, 0, 0], [0, 35, 0], [0, 0, -40], [20, -35, 40]])(
    "matches Three.js Euler XYZ for (%s, %s, %s)", (x, y, z) => {
      const point = new Vector3(13, 57, -19);
      const expected = point.clone().applyEuler(new Euler(x * Math.PI / 180, y * Math.PI / 180, z * Math.PI / 180, "XYZ"));
      expectPoint(rotatePoint(point, { x, y, z }), expected);
    },
  );

  it("keeps zero-rotation traced vertices at their saved min-corner positions", () => {
    const vertices = componentVertices(part);
    expectPoint(vertices[0], { x: 25, y: 450, z: 350 });
    expectPoint(vertices[2], { x: 70, y: 750, z: 350 });
    expectPoint(vertices[4], { x: 25, y: 450, z: 370 });
    expect(hasComponentRotation({ ...part, rotation_x: "360", rotation_y: "-720" })).toBe(false);
  });

  it("leans the upper end toward increasing rear Z for positive X tilt", () => {
    const vertices = componentVertices({ ...part, rotation_x: "10" });
    expect(vertices[2].z).toBeGreaterThan(vertices[1].z);
    // A front projection must also account for depth/height coupling.
    expect(projectComponent({ ...part, rotation_x: "10" }, "front").height).not.toBe(300);
  });

  it.each(["front", "side", "top"] as const)("fits the rotated box in the %s view", (view) => {
    const rotated = { ...part, rotation_x: "20", rotation_y: "-35", rotation_z: "40" };
    const vertices = componentVertices(rotated, true);
    const expected = new Box3().setFromPoints(vertices.map((point) => new Vector3(point.x, point.y, point.z)));
    const result = projectComponent(rotated, view);
    const horizontal = view === "side" ? "z" : "x", vertical = view === "top" ? "z" : "y";
    expect(result.horizontal).toBeCloseTo(expected.min[horizontal]);
    expect(result.vertical).toBeCloseTo(expected.min[vertical]);
    expect(result.width).toBeCloseTo(expected.max[horizontal] - expected.min[horizontal]);
    expect(result.height).toBeCloseTo(expected.max[vertical] - expected.min[vertical]);
  });

  it("snaps a rotated envelope by translation without rewriting its local size", () => {
    const rotated = { ...part, rotation_x: "15" };
    const projection = projectComponent(rotated, "side");
    const moved = applyProjectedPosition(rotated, "side", projection.horizontal + 10, projection.vertical - 5);
    expect(Number(moved.z)).toBeCloseTo(360);
    expect(Number(moved.y)).toBeCloseTo(445);
    expect(moved.width).toBe(rotated.width);
    expect(moved.height).toBe(rotated.height);
    expect(moved.rotation_x).toBe("15");
  });

  it("does not interpret a rotated projected envelope as local resizing/point movement", () => {
    const rotated = { ...part, rotation_x: "15" };
    expect(resizeComponent(rotated, "side", "north-east", 10, -10, 1, null)).toEqual(rotated);
    expect(moveProfilePoint(rotated, 2, 10, -10, 1, null)).toEqual(rotated);
    expect(resizeComponent(part, "front", "north-east", 10, -10, 1, null).width).toBe("80");
  });

  it("preserves a concave traced outline and either input winding", () => {
    const concave = { ...part, profile_points: [
      { u: "0", v: "0" }, { u: "70", v: "0" }, { u: "30", v: "100" },
      { u: "70", v: "300" }, { u: "0", v: "300" },
    ] };
    for (const points of [concave.profile_points, [...concave.profile_points].reverse()]) {
      const drawing = componentDrawing({ ...concave, profile_points: points }, "front");
      expect(drawing.faces).toHaveLength(1);
      expect(drawing.faces[0]).toHaveLength(5);
      expect(drawing.edges).toHaveLength(5);
      expect(drawing.faces[0]).toContainEqual({ horizontal: 55, vertical: 550 });
    }
  });

  it("draws only the outer boundary of shared box faces", () => {
    const box = { ...part, geometry_kind: "box" as const, profile_points: null };
    for (const view of ["front", "side", "top"] as const) {
      expect(componentDrawing(box, view).faces).toHaveLength(1);
      expect(componentDrawing(box, view).edges).toHaveLength(4);
    }
    const oblique = componentDrawing({ ...box, rotation_x: "20", rotation_y: "30", rotation_z: "10" }, "front");
    expect(oblique.faces.length).toBeGreaterThan(1);
    expect(oblique.edges).toHaveLength(6);
  });

  it("matches the actual centered 3D extrusion vertices after combined rotation", () => {
    const rotated = { ...part, rotation_x: "20", rotation_y: "-35", rotation_z: "40" };
    const geometry = buildCenteredProfileGeometry({ geometry_kind: part.geometry_kind,
      profile_points: part.profile_points, dimensions: { width: part.width, height: part.height, depth: part.depth! } })!;
    const expected = componentVertices(rotated);
    const euler = new Euler(20 * Math.PI / 180, -35 * Math.PI / 180, 40 * Math.PI / 180, "XYZ");
    const center = new Vector3(60, 600, 360);
    const positions = geometry.getAttribute("position");
    for (let index = 0; index < positions.count; index += 1) {
      const vertex = new Vector3().fromBufferAttribute(positions, index).applyEuler(euler).add(center);
      expect(Math.min(...expected.map((point) => vertex.distanceTo(new Vector3(point.x, point.y, point.z))))).toBeLessThan(0.001);
    }
    geometry.dispose();
    expect(buildCenteredProfileGeometry({ geometry_kind: "box", profile_points: null,
      dimensions: { width: "70", height: "300", depth: "20" } })).toBeNull();
  });
});
