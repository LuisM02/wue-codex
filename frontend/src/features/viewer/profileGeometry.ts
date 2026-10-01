import { ExtrudeGeometry, Shape } from "three";

import type { GeometryComponent } from "../../types/api";

export function buildCenteredProfileGeometry(
  part: Pick<GeometryComponent, "geometry_kind" | "profile_points" | "dimensions">,
): ExtrudeGeometry | null {
  if (part.geometry_kind !== "extruded_profile" || !part.profile_points?.length) return null;
  const shape = new Shape();
  shape.moveTo(Number(part.profile_points[0].u), Number(part.profile_points[0].v));
  part.profile_points.slice(1).forEach((point) => shape.lineTo(Number(point.u), Number(point.v)));
  shape.closePath();
  const geometry = new ExtrudeGeometry(shape, {
    depth: Number(part.dimensions.depth), bevelEnabled: false, curveSegments: 8,
  });
  // Match box geometry's center pivot without altering the saved local profile.
  geometry.translate(-Number(part.dimensions.width) / 2, -Number(part.dimensions.height) / 2,
    -Number(part.dimensions.depth) / 2);
  return geometry;
}
