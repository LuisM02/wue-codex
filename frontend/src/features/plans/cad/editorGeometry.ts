import type { FurnitureType, PlanComponent, PlanStatus } from "../../../types/api";
import { hasComponentRotation, projectedBox, type ProjectionView } from "../../../lib/componentPose";

export type OrthographicView = ProjectionView;
export const EDITOR_VIEWS = ["front", "back", "left", "right", "top"] as const;
export type ResizeHandle = "north-west" | "north-east" | "south-west" | "south-east";
export type AxisGuide = { axis: "horizontal" | "vertical"; value: number };

export interface ProjectionDefinition {
  horizontalPosition: "x" | "z";
  verticalPosition: "y" | "z";
  horizontalSize: "width" | "depth";
  verticalSize: "height" | "depth";
  horizontalLabel: "X" | "Z" | "−X" | "−Z";
  verticalLabel: "Y" | "Z";
  horizontalSign: 1 | -1;
}

export interface ProjectedComponent {
  horizontal: number;
  vertical: number;
  width: number;
  height: number;
}

export interface ProjectionBounds {
  minHorizontal: number;
  minVertical: number;
  maxHorizontal: number;
  maxVertical: number;
}

export const VIEW_DEFINITIONS: Record<OrthographicView, ProjectionDefinition> = {
  front: {
    horizontalPosition: "x",
    verticalPosition: "y",
    horizontalSize: "width",
    verticalSize: "height",
    horizontalLabel: "X",
    verticalLabel: "Y",
    horizontalSign: 1,
  },
  back: {
    horizontalPosition: "x", verticalPosition: "y",
    horizontalSize: "width", verticalSize: "height",
    horizontalLabel: "−X", verticalLabel: "Y", horizontalSign: -1,
  },
  left: {
    horizontalPosition: "z", verticalPosition: "y",
    horizontalSize: "depth", verticalSize: "height",
    horizontalLabel: "−Z", verticalLabel: "Y", horizontalSign: -1,
  },
  right: {
    horizontalPosition: "z", verticalPosition: "y",
    horizontalSize: "depth", verticalSize: "height",
    horizontalLabel: "Z", verticalLabel: "Y", horizontalSign: 1,
  },
  side: {
    horizontalPosition: "z",
    verticalPosition: "y",
    horizontalSize: "depth",
    verticalSize: "height",
    horizontalLabel: "Z",
    verticalLabel: "Y",
    horizontalSign: 1,
  },
  top: {
    horizontalPosition: "x",
    verticalPosition: "z",
    horizontalSize: "width",
    verticalSize: "depth",
    horizontalLabel: "X",
    verticalLabel: "Z",
    horizontalSign: 1,
  },
};

function numeric(value: string | null): number {
  const result = Number(value ?? 0);
  return Number.isFinite(result) ? result : 0;
}

function sizeField(
  component: PlanComponent,
  field: "width" | "height" | "depth",
): "width" | "height" | "depth" | "thickness" {
  return field === "depth" && component.depth === null && component.thickness !== null
    ? "thickness"
    : field;
}

function decimal(value: number): string {
  const safe = Math.abs(value) < 0.00005 ? 0 : value;
  return String(Math.round(safe * 10_000) / 10_000);
}

function positiveDecimal(value: number): string {
  return decimal(Math.max(0.0001, value));
}

type NumericPoint = { u: number; v: number };

function cross(first: NumericPoint, second: NumericPoint, third: NumericPoint): number {
  return (second.u - first.u) * (third.v - first.v)
    - (second.v - first.v) * (third.u - first.u);
}

function onSegment(first: NumericPoint, second: NumericPoint, point: NumericPoint): boolean {
  const epsilon = 0.0000001;
  return Math.abs(cross(first, second, point)) <= epsilon
    && point.u >= Math.min(first.u, second.u) - epsilon
    && point.u <= Math.max(first.u, second.u) + epsilon
    && point.v >= Math.min(first.v, second.v) - epsilon
    && point.v <= Math.max(first.v, second.v) + epsilon;
}

function segmentsIntersect(
  firstStart: NumericPoint,
  firstEnd: NumericPoint,
  secondStart: NumericPoint,
  secondEnd: NumericPoint,
): boolean {
  const firstCrossStart = cross(firstStart, firstEnd, secondStart);
  const firstCrossEnd = cross(firstStart, firstEnd, secondEnd);
  const secondCrossStart = cross(secondStart, secondEnd, firstStart);
  const secondCrossEnd = cross(secondStart, secondEnd, firstEnd);
  if (((firstCrossStart > 0 && firstCrossEnd < 0) || (firstCrossStart < 0 && firstCrossEnd > 0))
    && ((secondCrossStart > 0 && secondCrossEnd < 0) || (secondCrossStart < 0 && secondCrossEnd > 0))) {
    return true;
  }
  return onSegment(firstStart, firstEnd, secondStart)
    || onSegment(firstStart, firstEnd, secondEnd)
    || onSegment(secondStart, secondEnd, firstStart)
    || onSegment(secondStart, secondEnd, firstEnd);
}

export function isValidProfilePoints(points: Array<{ u: string; v: string }>): boolean {
  if (points.length < 3 || points.length > 256) return false;
  const numericPoints = points.map((point) => ({ u: numeric(point.u), v: numeric(point.v) }));
  const doubledArea = Math.abs(numericPoints.reduce((sum, point, index) => {
    const next = numericPoints[(index + 1) % numericPoints.length];
    return sum + point.u * next.v - next.u * point.v;
  }, 0));
  if (doubledArea < 0.0002) return false;
  for (let firstIndex = 0; firstIndex < numericPoints.length; firstIndex += 1) {
    const firstStart = numericPoints[firstIndex];
    const firstEnd = numericPoints[(firstIndex + 1) % numericPoints.length];
    if (firstStart.u === firstEnd.u && firstStart.v === firstEnd.v) return false;
    for (let secondIndex = firstIndex + 1; secondIndex < numericPoints.length; secondIndex += 1) {
      const adjacent = secondIndex === firstIndex
        || secondIndex === (firstIndex + 1) % numericPoints.length
        || firstIndex === (secondIndex + 1) % numericPoints.length;
      if (adjacent) continue;
      const secondStart = numericPoints[secondIndex];
      const secondEnd = numericPoints[(secondIndex + 1) % numericPoints.length];
      if (segmentsIntersect(firstStart, firstEnd, secondStart, secondEnd)) return false;
    }
  }
  return true;
}

export function projectComponent(
  component: PlanComponent,
  view: OrthographicView,
): ProjectedComponent {
  if (hasComponentRotation(component)) return projectedBox(component, view);
  const definition = VIEW_DEFINITIONS[view];
  const horizontalSize = sizeField(component, definition.horizontalSize);
  const verticalSize = sizeField(component, definition.verticalSize);
  return {
    horizontal: definition.horizontalSign === 1
      ? numeric(component[definition.horizontalPosition])
      : -numeric(component[definition.horizontalPosition]) - numeric(component[horizontalSize]),
    vertical: numeric(component[definition.verticalPosition]),
    width: numeric(component[horizontalSize]),
    height: numeric(component[verticalSize]),
  };
}

export function projectionBounds(
  components: PlanComponent[],
  view: OrthographicView,
): ProjectionBounds {
  if (!components.length) {
    return { minHorizontal: 0, minVertical: 0, maxHorizontal: 100, maxVertical: 100 };
  }
  const projected = components.map((component) => projectComponent(component, view));
  return {
    minHorizontal: Math.min(0, ...projected.map((item) => item.horizontal)),
    minVertical: Math.min(0, ...projected.map((item) => item.vertical)),
    maxHorizontal: Math.max(1, ...projected.map((item) => item.horizontal + item.width)),
    maxVertical: Math.max(1, ...projected.map((item) => item.vertical + item.height)),
  };
}

export function screenDeltaToWorld(
  deltaX: number,
  deltaY: number,
  scale: number,
): { horizontal: number; vertical: number } {
  return {
    horizontal: deltaX / Math.max(scale, 0.0001),
    vertical: -deltaY / Math.max(scale, 0.0001),
  };
}

export function snapToGrid(value: number, spacing: number): number {
  if (!Number.isFinite(spacing) || spacing <= 0) return value;
  const snapped = Math.round(value / spacing) * spacing;
  return Object.is(snapped, -0) ? 0 : snapped;
}

export function moveComponent(
  component: PlanComponent,
  view: OrthographicView,
  deltaX: number,
  deltaY: number,
  scale: number,
  gridSpacing: number | null,
): PlanComponent {
  const definition = VIEW_DEFINITIONS[view];
  const delta = screenDeltaToWorld(deltaX, deltaY, scale);
  const horizontal = numeric(component[definition.horizontalPosition]) + definition.horizontalSign * delta.horizontal;
  const vertical = numeric(component[definition.verticalPosition]) + delta.vertical;
  return {
    ...component,
    [definition.horizontalPosition]: decimal(
      gridSpacing ? snapToGrid(horizontal, gridSpacing) : horizontal,
    ),
    [definition.verticalPosition]: decimal(
      gridSpacing ? snapToGrid(vertical, gridSpacing) : vertical,
    ),
  };
}

export function edgeSnap(
  moving: ProjectedComponent,
  others: ProjectedComponent[],
  tolerance: number,
): { horizontal: number; vertical: number; guides: AxisGuide[] } {
  let horizontal = moving.horizontal;
  let vertical = moving.vertical;
  const guides: AxisGuide[] = [];
  const movingHorizontalEdges = [moving.horizontal, moving.horizontal + moving.width];
  const movingVerticalEdges = [moving.vertical, moving.vertical + moving.height];
  const otherHorizontalEdges = others.flatMap((item) => [item.horizontal, item.horizontal + item.width]);
  const otherVerticalEdges = others.flatMap((item) => [item.vertical, item.vertical + item.height]);
  let bestHorizontal: { distance: number; adjustment: number; value: number } | null = null;
  let bestVertical: { distance: number; adjustment: number; value: number } | null = null;
  for (const source of movingHorizontalEdges) {
    for (const target of otherHorizontalEdges) {
      const distance = Math.abs(target - source);
      if (distance <= tolerance && (!bestHorizontal || distance < bestHorizontal.distance)) {
        bestHorizontal = { distance, adjustment: target - source, value: target };
      }
    }
  }
  for (const source of movingVerticalEdges) {
    for (const target of otherVerticalEdges) {
      const distance = Math.abs(target - source);
      if (distance <= tolerance && (!bestVertical || distance < bestVertical.distance)) {
        bestVertical = { distance, adjustment: target - source, value: target };
      }
    }
  }
  if (bestHorizontal) {
    horizontal += bestHorizontal.adjustment;
    guides.push({ axis: "vertical", value: bestHorizontal.value });
  }
  if (bestVertical) {
    vertical += bestVertical.adjustment;
    guides.push({ axis: "horizontal", value: bestVertical.value });
  }
  return { horizontal, vertical, guides };
}

export function applyProjectedPosition(
  component: PlanComponent,
  view: OrthographicView,
  horizontal: number,
  vertical: number,
): PlanComponent {
  const definition = VIEW_DEFINITIONS[view];
  const projected = projectComponent(component, view);
  return {
    ...component,
    [definition.horizontalPosition]: decimal(numeric(component[definition.horizontalPosition]) + definition.horizontalSign * (horizontal - projected.horizontal)),
    [definition.verticalPosition]: decimal(numeric(component[definition.verticalPosition]) + vertical - projected.vertical),
  };
}

export function resizeComponent(
  component: PlanComponent,
  view: OrthographicView,
  handle: ResizeHandle,
  deltaX: number,
  deltaY: number,
  scale: number,
  gridSpacing: number | null,
): PlanComponent {
  // A rotated projected envelope is not a local size. Use exact Properties
  // until inverse-pose resizing is implemented instead of corrupting dimensions.
  if (hasComponentRotation(component)) return component;
  const definition = VIEW_DEFINITIONS[view];
  const horizontalSize = sizeField(component, definition.horizontalSize);
  const verticalSize = sizeField(component, definition.verticalSize);
  const projected = projectComponent(component, view);
  const delta = screenDeltaToWorld(deltaX, deltaY, scale);
  const west = handle.endsWith("west");
  const north = handle.startsWith("north");
  let horizontal = projected.horizontal;
  let vertical = projected.vertical;
  let width = west ? projected.width - delta.horizontal : projected.width + delta.horizontal;
  let height = north ? projected.height + delta.vertical : projected.height - delta.vertical;
  if (west) horizontal = projected.horizontal + delta.horizontal;
  if (!north) vertical = projected.vertical + delta.vertical;
  if (gridSpacing) {
    horizontal = snapToGrid(horizontal, gridSpacing);
    vertical = snapToGrid(vertical, gridSpacing);
    width = snapToGrid(width, gridSpacing);
    height = snapToGrid(height, gridSpacing);
  }
  const minimum = gridSpacing ? Math.min(gridSpacing, 1) : 0.0001;
  if (width <= 0 || height <= 0) return component;
  width = Math.max(minimum, width);
  height = Math.max(minimum, height);

  const next: PlanComponent = {
    ...component,
    [definition.horizontalPosition]: decimal(definition.horizontalSign === 1 ? horizontal : -horizontal - width),
    [definition.verticalPosition]: decimal(vertical),
    [horizontalSize]: positiveDecimal(width),
    [verticalSize]: positiveDecimal(height),
  };
  if (component.profile_points) {
    const widthScale = numeric(next.width) / Math.max(numeric(component.width), 0.0001);
    const heightScale = numeric(next.height) / Math.max(numeric(component.height), 0.0001);
    next.profile_points = component.profile_points.map((point) => ({
      u: decimal(numeric(point.u) * widthScale),
      v: decimal(numeric(point.v) * heightScale),
    }));
  }
  return next;
}

export function moveProfilePoint(
  component: PlanComponent,
  pointIndex: number,
  deltaX: number,
  deltaY: number,
  scale: number,
  gridSpacing: number | null,
  horizontalSign: 1 | -1 = 1,
): PlanComponent {
  if (hasComponentRotation(component)) return component;
  if (component.geometry_kind !== "extruded_profile" || !component.profile_points?.[pointIndex]) {
    return component;
  }
  const delta = screenDeltaToWorld(deltaX, deltaY, scale);
  const original = component.profile_points[pointIndex];
  const width = numeric(component.width);
  const height = numeric(component.height);
  let u = numeric(original.u) + horizontalSign * delta.horizontal;
  let v = numeric(original.v) + delta.vertical;
  if (gridSpacing) {
    u = snapToGrid(u, gridSpacing);
    v = snapToGrid(v, gridSpacing);
  }
  u = Math.min(width, Math.max(0, u));
  v = Math.min(height, Math.max(0, v));
  const points = component.profile_points.map((point, index) => index === pointIndex
    ? { u: decimal(u), v: decimal(v) }
    : point);
  if (!isValidProfilePoints(points)) return component;
  return { ...component, profile_points: points };
}

export function longestProfileEdgeIndex(points: Array<{ u: string; v: string }>): number {
  if (!points.length) return -1;
  let longestIndex = 0;
  let longestSquaredLength = -1;
  points.forEach((point, index) => {
    const next = points[(index + 1) % points.length];
    const deltaU = numeric(next.u) - numeric(point.u);
    const deltaV = numeric(next.v) - numeric(point.v);
    const squaredLength = deltaU * deltaU + deltaV * deltaV;
    if (squaredLength > longestSquaredLength) {
      longestIndex = index;
      longestSquaredLength = squaredLength;
    }
  });
  return longestIndex;
}

export function insertProfilePoint(component: PlanComponent, afterIndex: number | null): PlanComponent {
  const points = component.profile_points;
  if (component.geometry_kind !== "extruded_profile" || !points || points.length >= 256) return component;
  const edgeIndex = afterIndex === null ? longestProfileEdgeIndex(points) : afterIndex;
  if (edgeIndex < 0 || edgeIndex >= points.length) return component;
  const point = points[edgeIndex];
  const next = points[(edgeIndex + 1) % points.length];
  const inserted = {
    u: decimal((numeric(point.u) + numeric(next.u)) / 2),
    v: decimal((numeric(point.v) + numeric(next.v)) / 2),
  };
  const profilePoints = [...points.slice(0, edgeIndex + 1), inserted, ...points.slice(edgeIndex + 1)];
  return isValidProfilePoints(profilePoints) ? { ...component, profile_points: profilePoints } : component;
}

export function removeProfilePoint(component: PlanComponent, pointIndex: number): PlanComponent {
  const points = component.profile_points;
  if (component.geometry_kind !== "extruded_profile" || !points || points.length <= 3
    || pointIndex < 0 || pointIndex >= points.length) return component;
  const profilePoints = points.filter((_, index) => index !== pointIndex);
  return isValidProfilePoints(profilePoints) ? { ...component, profile_points: profilePoints } : component;
}

export function nextShelfName(components: PlanComponent[]): string {
  const used = new Set(
    components
      .map((component) => /^shelf_([1-9]\d*)$/.exec(component.component_name)?.[1])
      .filter((value): value is string => Boolean(value))
      .map(Number),
  );
  let number = 1;
  while (used.has(number)) number += 1;
  return `shelf_${number}`;
}

export function canMutatePlan(status: PlanStatus): boolean {
  return status === "draft";
}

export function semanticWarnings(
  furnitureType: FurnitureType,
  components: PlanComponent[],
): string[] {
  const count = (name: string, type: "panel" | "leg") =>
    components.filter((component) => component.component_name === name && component.component_type === type).length;
  const legs = components.filter((component) => component.component_type === "leg").length;
  const warnings: string[] = [];
  if (furnitureType === "chair") {
    if (!legs) warnings.push("Add at least one leg before finishing 2D.");
    if (count("seat", "panel") !== 1) warnings.push("The chair needs exactly one seat panel.");
    if (count("backrest", "panel") !== 1) warnings.push("The chair needs exactly one backrest panel.");
  } else if (furnitureType === "dining_table") {
    if (!legs) warnings.push("Add at least one leg before finishing 2D.");
    if (count("tabletop", "panel") !== 1) warnings.push("The table needs exactly one tabletop panel.");
  } else {
    for (const name of ["left_side", "right_side", "top_panel", "bottom_panel", "back_panel"]) {
      if (count(name, "panel") !== 1) warnings.push(`The bookshelf needs exactly one ${name.replaceAll("_", " ")} panel.`);
    }
    if (!components.some((component) => /^shelf_[1-9]\d*$/.test(component.component_name) && component.component_type === "panel")) {
      warnings.push("Add at least one correctly named shelf before finishing 2D.");
    }
  }
  return warnings;
}
