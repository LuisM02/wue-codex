import type { FurnitureType, PlanComponent, PlanStatus } from "../../../types/api";

export type OrthographicView = "front" | "side" | "top";
export type ResizeHandle = "north-west" | "north-east" | "south-west" | "south-east";
export type AxisGuide = { axis: "horizontal" | "vertical"; value: number };

export interface ProjectionDefinition {
  horizontalPosition: "x" | "z";
  verticalPosition: "y" | "z";
  horizontalSize: "width" | "depth";
  verticalSize: "height" | "depth";
  horizontalLabel: "X" | "Z";
  verticalLabel: "Y" | "Z";
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
  },
  side: {
    horizontalPosition: "z",
    verticalPosition: "y",
    horizontalSize: "depth",
    verticalSize: "height",
    horizontalLabel: "Z",
    verticalLabel: "Y",
  },
  top: {
    horizontalPosition: "x",
    verticalPosition: "z",
    horizontalSize: "width",
    verticalSize: "depth",
    horizontalLabel: "X",
    verticalLabel: "Z",
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

export function projectComponent(
  component: PlanComponent,
  view: OrthographicView,
): ProjectedComponent {
  const definition = VIEW_DEFINITIONS[view];
  const horizontalSize = sizeField(component, definition.horizontalSize);
  const verticalSize = sizeField(component, definition.verticalSize);
  return {
    horizontal: numeric(component[definition.horizontalPosition]),
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
  const horizontal = numeric(component[definition.horizontalPosition]) + delta.horizontal;
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
  return {
    ...component,
    [definition.horizontalPosition]: decimal(horizontal),
    [definition.verticalPosition]: decimal(vertical),
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
    [definition.horizontalPosition]: decimal(horizontal),
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
