import type { PlanComponent } from "../types/api";

// "side" is retained as the historical right-side projection for callers.
export type ProjectionView = "front" | "back" | "left" | "right" | "side" | "top";
export type Point3 = { x: number; y: number; z: number };
export type Point2 = { horizontal: number; vertical: number };
type PoseComponent = Pick<PlanComponent,
  "width" | "height" | "depth" | "thickness" | "x" | "y" | "z"
  | "rotation_x" | "rotation_y" | "rotation_z" | "geometry_kind" | "profile_points">;

function number(value: string | null): number {
  const result = Number(value ?? 0);
  return Number.isFinite(result) ? result : 0;
}

export function hasComponentRotation(component: PoseComponent): boolean {
  return [component.rotation_x, component.rotation_y, component.rotation_z]
    .some((value) => Math.abs(number(value) % 360) > 0.00000001);
}

/** Three.js Euler XYZ: apply local Z, then Y, then X, about the part center. */
export function rotatePoint(point: Point3, degrees: Point3): Point3 {
  const [x, y, z] = [degrees.x, degrees.y, degrees.z].map((angle) => angle * Math.PI / 180);
  const zx = Math.cos(z) * point.x - Math.sin(z) * point.y;
  const zy = Math.sin(z) * point.x + Math.cos(z) * point.y;
  const yx = Math.cos(y) * zx + Math.sin(y) * point.z;
  const yz = -Math.sin(y) * zx + Math.cos(y) * point.z;
  return {
    x: yx,
    y: Math.cos(x) * zy - Math.sin(x) * yz,
    z: Math.sin(x) * zy + Math.cos(x) * yz,
  };
}

function profile(component: PoseComponent, boundingBox = false): Array<{ u: number; v: number }> {
  const width = number(component.width), height = number(component.height);
  return !boundingBox && component.geometry_kind === "extruded_profile" && component.profile_points?.length
    ? component.profile_points.map((point) => ({ u: number(point.u), v: number(point.v) }))
    : [{ u: 0, v: 0 }, { u: width, v: 0 }, { u: width, v: height }, { u: 0, v: height }];
}

function rotation(component: PoseComponent): Point3 {
  return { x: number(component.rotation_x), y: number(component.rotation_y), z: number(component.rotation_z) };
}

export function componentVertices(component: PoseComponent, boundingBox = false): Point3[] {
  const width = number(component.width), height = number(component.height);
  const depth = number(component.depth ?? component.thickness);
  const center = { x: number(component.x) + width / 2, y: number(component.y) + height / 2,
    z: number(component.z) + depth / 2 };
  return [0, depth].flatMap((z) => profile(component, boundingBox).map((point) => {
    const rotated = rotatePoint({ x: point.u - width / 2, y: point.v - height / 2, z: z - depth / 2 }, rotation(component));
    return { x: rotated.x + center.x, y: rotated.y + center.y, z: rotated.z + center.z };
  }));
}

export function projectPoint(point: Point3, view: ProjectionView): Point2 {
  const side = view === "side" || view === "left" || view === "right";
  const sign = view === "back" || view === "left" ? -1 : 1;
  return { horizontal: sign * (side ? point.z : point.x),
    vertical: view === "top" ? point.z : point.y };
}

export function projectedBox(component: PoseComponent, view: ProjectionView) {
  const points = componentVertices(component, true).map((point) => projectPoint(point, view));
  const horizontal = Math.min(...points.map((point) => point.horizontal));
  const vertical = Math.min(...points.map((point) => point.vertical));
  return { horizontal, vertical,
    width: Math.max(...points.map((point) => point.horizontal)) - horizontal,
    height: Math.max(...points.map((point) => point.vertical)) - vertical };
}

/** Visible projected faces and silhouette edges; retain concave traced profiles. */
export function componentDrawing(component: PoseComponent, view: ProjectionView) {
  const points = profile(component), count = points.length;
  const vertices = componentVertices(component).map((point) => projectPoint(point, view));
  const area = points.reduce((sum, point, index) => {
    const next = points[(index + 1) % count];
    return sum + point.u * next.v - next.u * point.v;
  }, 0);
  const winding = area >= 0 ? 1 : -1;
  const faces = [
    { indices: points.map((_, index) => index), normal: { x: 0, y: 0, z: -1 } },
    { indices: points.map((_, index) => index + count), normal: { x: 0, y: 0, z: 1 } },
    ...points.map((point, index) => {
      const nextIndex = (index + 1) % count, next = points[nextIndex];
      return { indices: [index, nextIndex, nextIndex + count, index + count],
        normal: { x: winding * (next.v - point.v), y: winding * (point.u - next.u), z: 0 } };
    }),
  ];
  const edges = new Map<string, { indices: [number, number]; visible: number }>();
  const visibleFaces: Point2[][] = [];
  for (const face of faces) {
    const normal = rotatePoint(face.normal, rotation(component));
    const facing = view === "front" ? -normal.z : view === "back" ? normal.z
      : view === "left" ? -normal.x : view === "right" || view === "side" ? normal.x : normal.y;
    const visible = facing > 0.00000001;
    if (visible) visibleFaces.push(face.indices.map((index) => vertices[index]));
    face.indices.forEach((first, index) => {
      const second = face.indices[(index + 1) % face.indices.length];
      const key = first < second ? `${first}:${second}` : `${second}:${first}`;
      const edge = edges.get(key) ?? { indices: [first, second] as [number, number], visible: 0 };
      edge.visible += visible ? 1 : 0;
      edges.set(key, edge);
    });
  }
  return { faces: visibleFaces,
    edges: [...edges.values()].filter((edge) => edge.visible === 1)
      .map((edge) => edge.indices.map((index) => vertices[index]) as [Point2, Point2]) };
}
