import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent as ReactPointerEvent, WheelEvent as ReactWheelEvent } from "react";

import type { ImageView, PlanComponent } from "../../../types/api";
import {
  VIEW_DEFINITIONS,
  applyProjectedPosition,
  edgeSnap,
  insertProfilePoint,
  longestProfileEdgeIndex,
  moveComponent,
  moveProfilePoint,
  projectComponent,
  projectionBounds,
  removeProfilePoint,
  resizeComponent,
  type AxisGuide,
  type OrthographicView,
  type ResizeHandle,
} from "./editorGeometry";
import type { ReferenceOption } from "./referencePhotos";

const CANVAS_WIDTH = 1000;
const CANVAS_HEIGHT = 620;
const MARGIN_X = 88;
const MARGIN_Y = 64;
const GRID_SPACING_MM = 25;
const OUTLINE_SNAP_MM = 5;

interface Props {
  components: PlanComponent[];
  selectedId: string | null;
  view: OrthographicView;
  locked: boolean;
  gridVisible: boolean;
  snapEnabled: boolean;
  referenceImageUrl?: string;
  referenceView: ImageView | null;
  referenceMirrored: boolean;
  referenceOptions: ReferenceOption[];
  photoVisible: boolean;
  zoom: number;
  pan: { x: number; y: number };
  onPan: (pan: { x: number; y: number }) => void;
  onZoom: (direction: 1 | -1) => void;
  onReference: (view: ImageView) => void;
  onMirror: () => void;
  onSelect: (id: string | null) => void;
  onPreview: (component: PlanComponent) => void;
  onCommit: (before: PlanComponent, after: PlanComponent) => void;
}

type Interaction =
  | { type: "move"; pointerId: number; start: { x: number; y: number }; before: PlanComponent }
  | { type: "resize"; pointerId: number; start: { x: number; y: number }; before: PlanComponent; handle: ResizeHandle }
  | { type: "profile-point"; pointerId: number; start: { x: number; y: number }; before: PlanComponent; pointIndex: number }
  | { type: "pan"; pointerId: number; start: { x: number; y: number }; before: { x: number; y: number } };

function clientPoint(event: ReactPointerEvent<SVGElement>): { x: number; y: number } {
  const rect = event.currentTarget.ownerSVGElement?.getBoundingClientRect() ?? event.currentTarget.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left) * (CANVAS_WIDTH / Math.max(rect.width, 1)),
    y: (event.clientY - rect.top) * (CANVAS_HEIGHT / Math.max(rect.height, 1)),
  };
}

function sameGeometry(first: PlanComponent, second: PlanComponent): boolean {
  const fields = ["x", "y", "z", "width", "height", "depth", "profile_points"] as const;
  return fields.every((field) => JSON.stringify(first[field]) === JSON.stringify(second[field]));
}

export function CanvasWorkspace({
  components,
  selectedId,
  view,
  locked,
  gridVisible,
  snapEnabled,
  referenceImageUrl,
  referenceView,
  referenceMirrored,
  referenceOptions,
  photoVisible,
  zoom,
  pan,
  onPan,
  onZoom,
  onReference,
  onMirror,
  onSelect,
  onPreview,
  onCommit,
}: Props) {
  const interaction = useRef<Interaction | null>(null);
  const [guides, setGuides] = useState<AxisGuide[]>([]);
  const [selectedProfilePoint, setSelectedProfilePoint] = useState<number | null>(null);
  const bounds = useMemo(() => projectionBounds(components, view), [components, view]);
  const spanHorizontal = Math.max(1, bounds.maxHorizontal - bounds.minHorizontal);
  const spanVertical = Math.max(1, bounds.maxVertical - bounds.minVertical);
  const fitScale = Math.min(
    (CANVAS_WIDTH - MARGIN_X * 2) / spanHorizontal,
    (CANVAS_HEIGHT - MARGIN_Y * 2) / spanVertical,
  );
  const scale = Math.max(0.02, fitScale * zoom);
  const originX = (CANVAS_WIDTH - spanHorizontal * scale) / 2 - bounds.minHorizontal * scale + pan.x;
  const originY = (CANVAS_HEIGHT - spanVertical * scale) / 2 + bounds.maxVertical * scale + pan.y;
  const toScreenHorizontal = (value: number) => originX + value * scale;
  const toScreenVertical = (value: number) => originY - value * scale;
  const definition = VIEW_DEFINITIONS[view];
  const selected = components.find((component) => component.id === selectedId) ?? null;
  const selectedProjection = selected ? projectComponent(selected, view) : null;
  const visibleGridSpacing = GRID_SPACING_MM * Math.max(1, Math.ceil(20 / Math.max(GRID_SPACING_MM * scale, 1)));
  const gridPixels = visibleGridSpacing * scale;

  useEffect(() => {
    setSelectedProfilePoint(null);
  }, [selectedId, view]);

  function beginMove(event: ReactPointerEvent<SVGGElement>, component: PlanComponent) {
    event.stopPropagation();
    onSelect(component.id);
    setSelectedProfilePoint(null);
    if (locked || event.button !== 0) return;
    const point = clientPoint(event);
    interaction.current = { type: "move", pointerId: event.pointerId, start: point, before: component };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function beginResize(event: ReactPointerEvent<SVGRectElement>, component: PlanComponent, handle: ResizeHandle) {
    event.stopPropagation();
    if (locked || event.button !== 0) return;
    const point = clientPoint(event);
    interaction.current = { type: "resize", pointerId: event.pointerId, start: point, before: component, handle };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function beginProfilePoint(event: ReactPointerEvent<SVGCircleElement>, component: PlanComponent, pointIndex: number) {
    event.stopPropagation();
    if (locked || event.button !== 0) return;
    setSelectedProfilePoint(pointIndex);
    interaction.current = {
      type: "profile-point",
      pointerId: event.pointerId,
      start: clientPoint(event),
      before: component,
      pointIndex,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function beginCanvas(event: ReactPointerEvent<SVGRectElement>) {
    if (event.button === 1 || event.altKey) {
      event.preventDefault();
      interaction.current = { type: "pan", pointerId: event.pointerId, start: clientPoint(event), before: pan };
      event.currentTarget.setPointerCapture(event.pointerId);
    } else if (event.button === 0) {
      onSelect(null);
      setSelectedProfilePoint(null);
    }
  }

  function pointerMove(event: ReactPointerEvent<SVGSVGElement>) {
    const active = interaction.current;
    if (!active || active.pointerId !== event.pointerId) return;
    const point = clientPoint(event);
    const deltaX = point.x - active.start.x;
    const deltaY = point.y - active.start.y;
    if (active.type === "pan") {
      onPan({ x: active.before.x + deltaX, y: active.before.y + deltaY });
      return;
    }
    if (active.type === "resize") {
      onPreview(
        resizeComponent(
          active.before,
          view,
          active.handle,
          deltaX,
          deltaY,
          scale,
          snapEnabled ? GRID_SPACING_MM : null,
        ),
      );
      return;
    }
    if (active.type === "profile-point") {
      onPreview(
        moveProfilePoint(
          active.before,
          active.pointIndex,
          deltaX,
          deltaY,
          scale,
          snapEnabled ? OUTLINE_SNAP_MM : null,
        ),
      );
      return;
    }
    let moved = moveComponent(
      active.before,
      view,
      deltaX,
      deltaY,
      scale,
      snapEnabled ? GRID_SPACING_MM : null,
    );
    if (snapEnabled) {
      const snap = edgeSnap(
        projectComponent(moved, view),
        components.filter((component) => component.id !== moved.id).map((component) => projectComponent(component, view)),
        8 / scale,
      );
      moved = applyProjectedPosition(moved, view, snap.horizontal, snap.vertical);
      setGuides(snap.guides);
    }
    onPreview(moved);
  }

  function endPointer(event: ReactPointerEvent<SVGSVGElement>) {
    const active = interaction.current;
    if (!active || active.pointerId !== event.pointerId) return;
    interaction.current = null;
    setGuides([]);
    if (active.type === "pan") return;
    const after = components.find((component) => component.id === active.before.id);
    if (after && !sameGeometry(active.before, after)) onCommit(active.before, after);
  }

  function wheel(event: ReactWheelEvent<SVGSVGElement>) {
    event.preventDefault();
    onZoom(event.deltaY < 0 ? 1 : -1);
  }

  function addOutlinePoint() {
    if (locked || view !== "front" || !selected?.profile_points) return;
    const edgeIndex = selectedProfilePoint ?? longestProfileEdgeIndex(selected.profile_points);
    const after = insertProfilePoint(selected, edgeIndex);
    if (sameGeometry(selected, after)) return;
    onPreview(after);
    onCommit(selected, after);
    setSelectedProfilePoint(edgeIndex + 1);
  }

  function removeOutlinePoint(pointIndex = selectedProfilePoint) {
    if (locked || view !== "front" || !selected || pointIndex === null) return;
    const after = removeProfilePoint(selected, pointIndex);
    if (sameGeometry(selected, after)) return;
    onPreview(after);
    onCommit(selected, after);
    setSelectedProfilePoint(null);
  }

  const ordered = [...components].sort((first, second) => {
    if (first.id === selectedId) return 1;
    if (second.id === selectedId) return -1;
    return first.sort_order - second.sort_order;
  });

  return (
    <main className="cad-workspace">
      <div className="cad-canvas-frame">
        {referenceOptions.length > 0 && (
          <div className="cad-reference-controls" role="group" aria-label="Reference photograph controls">
            <label>
              <span>Reference</span>
              <select
                aria-label="Reference photograph"
                value={referenceView ?? ""}
                onChange={(event) => onReference(event.target.value as ImageView)}
              >
                {referenceOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <button type="button" aria-pressed={referenceMirrored} onClick={onMirror} title="Mirror the reference photograph horizontally">↔ Mirror</button>
          </div>
        )}
        <svg
          viewBox={`0 0 ${CANVAS_WIDTH} ${CANVAS_HEIGHT}`}
          role="img"
          aria-label={`${view} orthographic furniture drawing`}
          onPointerMove={pointerMove}
          onPointerUp={endPointer}
          onPointerCancel={endPointer}
          onWheel={wheel}
        >
          <defs>
            <pattern id="cad-minor-grid" width={gridPixels} height={gridPixels} patternUnits="userSpaceOnUse" x={originX % gridPixels} y={originY % gridPixels}>
              <path d={`M ${gridPixels} 0 L 0 0 0 ${gridPixels}`} className="cad-grid-line" fill="none" />
            </pattern>
            <marker id="cad-dimension-arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0L10 5L0 10z" className="cad-dimension-arrow" />
            </marker>
          </defs>
          <rect className="cad-canvas-background" width={CANVAS_WIDTH} height={CANVAS_HEIGHT} onPointerDown={beginCanvas} />
          {gridVisible && <rect className="cad-grid" width={CANVAS_WIDTH} height={CANVAS_HEIGHT} fill="url(#cad-minor-grid)" pointerEvents="none" />}
          {referenceImageUrl && photoVisible && (
            <image
              href={referenceImageUrl}
              x="0"
              y="0"
              width={CANVAS_WIDTH}
              height={CANVAS_HEIGHT}
              preserveAspectRatio="xMidYMid meet"
              className="cad-reference-photo"
              pointerEvents="none"
              transform={referenceMirrored ? `translate(${CANVAS_WIDTH} 0) scale(-1 1)` : undefined}
            />
          )}
          {view !== "top" && (
            <line className="cad-ground-line" x1="24" x2={CANVAS_WIDTH - 24} y1={toScreenVertical(0)} y2={toScreenVertical(0)} />
          )}
          {guides.map((guide, index) => guide.axis === "vertical" ? (
            <line key={`${guide.axis}-${index}`} className="cad-snap-guide" x1={toScreenHorizontal(guide.value)} x2={toScreenHorizontal(guide.value)} y1="0" y2={CANVAS_HEIGHT} />
          ) : (
            <line key={`${guide.axis}-${index}`} className="cad-snap-guide" x1="0" x2={CANVAS_WIDTH} y1={toScreenVertical(guide.value)} y2={toScreenVertical(guide.value)} />
          ))}
          {ordered.map((component) => {
            const projected = projectComponent(component, view);
            const left = toScreenHorizontal(projected.horizontal);
            const top = toScreenVertical(projected.vertical + projected.height);
            const width = Math.max(2, projected.width * scale);
            const height = Math.max(2, projected.height * scale);
            const centerX = left + width / 2;
            const centerY = top + height / 2;
            const rotation = view === "front" ? -Number(component.rotation_z) : view === "side" ? -Number(component.rotation_x) : -Number(component.rotation_y);
            const selectedShape = component.id === selectedId;
            const polygon = view === "front" && component.geometry_kind === "extruded_profile" && component.profile_points
              ? component.profile_points.map((point) => `${left + Number(point.u) * scale},${toScreenVertical(projected.vertical + Number(point.v))}`).join(" ")
              : null;
            return (
              <g
                key={component.id}
                className={`cad-component-shape${selectedShape ? " is-selected" : ""}${locked ? " is-locked" : ""}`}
                transform={rotation ? `rotate(${rotation} ${centerX} ${centerY})` : undefined}
                onPointerDown={(event) => beginMove(event, component)}
                tabIndex={0}
                role="button"
                aria-label={`Select ${component.component_name.replaceAll("_", " ")}`}
                onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onSelect(component.id); }}
              >
                {polygon ? <polygon points={polygon} /> : <rect x={left} y={top} width={width} height={height} rx="1.5" />}
                {width > 52 && height > 22 && <text x={centerX} y={centerY + 3} textAnchor="middle">{component.component_name.replaceAll("_", " ")}</text>}
              </g>
            );
          })}
          {selected && selectedProjection && (() => {
            const left = toScreenHorizontal(selectedProjection.horizontal);
            const right = toScreenHorizontal(selectedProjection.horizontal + selectedProjection.width);
            const top = toScreenVertical(selectedProjection.vertical + selectedProjection.height);
            const bottom = toScreenVertical(selectedProjection.vertical);
            const handles: Array<[ResizeHandle, number, number]> = [
              ["north-west", left, top],
              ["north-east", right, top],
              ["south-west", left, bottom],
              ["south-east", right, bottom],
            ];
            return (
              <g className="cad-selection-overlay">
                <rect x={left} y={top} width={Math.max(2, right - left)} height={Math.max(2, bottom - top)} className="cad-selection-box" />
                {!locked && handles.map(([handle, x, y]) => (
                  <rect
                    key={handle}
                    x={x - 5}
                    y={y - 5}
                    width="10"
                    height="10"
                    className="cad-resize-handle"
                    pointerEvents="all"
                    onPointerDown={(event) => beginResize(event, selected, handle)}
                  />
                ))}
                {!locked && view === "front" && selected.profile_points?.map((point, pointIndex) => (
                  <circle
                    key={`profile-point-${pointIndex}`}
                    cx={toScreenHorizontal(selectedProjection.horizontal + Number(point.u))}
                    cy={toScreenVertical(selectedProjection.vertical + Number(point.v))}
                    r="6"
                    className={`cad-profile-handle${selectedProfilePoint === pointIndex ? " is-active" : ""}`}
                    pointerEvents="all"
                    aria-label={`Move outline point ${pointIndex + 1}`}
                    aria-pressed={selectedProfilePoint === pointIndex}
                    role="button"
                    tabIndex={0}
                    onPointerDown={(event) => beginProfilePoint(event, selected, pointIndex)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        event.stopPropagation();
                        setSelectedProfilePoint(pointIndex);
                      } else if (event.key === "Delete" || event.key === "Backspace") {
                        event.preventDefault();
                        event.stopPropagation();
                        removeOutlinePoint(pointIndex);
                      }
                    }}
                  />
                ))}
                <g className="cad-dimension" pointerEvents="none">
                  <line x1={left} x2={right} y1={bottom + 28} y2={bottom + 28} markerStart="url(#cad-dimension-arrow)" markerEnd="url(#cad-dimension-arrow)" />
                  <text x={(left + right) / 2} y={bottom + 22} textAnchor="middle">{selectedProjection.width.toFixed(1)} mm</text>
                  <line x1={left - 28} x2={left - 28} y1={top} y2={bottom} markerStart="url(#cad-dimension-arrow)" markerEnd="url(#cad-dimension-arrow)" />
                  <text x={left - 35} y={(top + bottom) / 2} textAnchor="middle" transform={`rotate(-90 ${left - 35} ${(top + bottom) / 2})`}>{selectedProjection.height.toFixed(1)} mm</text>
                </g>
              </g>
            );
          })()}
          <g className="cad-axis-indicator" transform={`translate(${CANVAS_WIDTH - 70} ${CANVAS_HEIGHT - 55})`}>
            <line x1="0" y1="0" x2="38" y2="0" />
            <line x1="0" y1="0" x2="0" y2="-38" />
            <text x="44" y="4">{definition.horizontalLabel}</text>
            <text x="-3" y="-45">{definition.verticalLabel}</text>
          </g>
          <text x="24" y="31" className="cad-view-title">{view.toUpperCase()} VIEW · CANONICAL MM</text>
        </svg>
      </div>
      <footer className="cad-statusbar">
        <span>{locked
          ? "Read-only inspection"
          : view === "front" && selected?.profile_points
            ? "Drag round points to reshape the traced outline · square handles resize the whole part"
            : "Drag parts · drag corner handles to resize · Alt-drag or middle-drag to pan"}</span>
        {view === "front" && selected?.profile_points && !locked ? (
          <div className="cad-outline-actions" role="toolbar" aria-label="Traced outline points">
            <span>{selected.profile_points.length} points</span>
            <button type="button" onClick={addOutlinePoint} disabled={selected.profile_points.length >= 256}>＋ Add point</button>
            <button type="button" onClick={() => removeOutlinePoint()} disabled={selectedProfilePoint === null || selected.profile_points.length <= 3}>− Remove selected</button>
          </div>
        ) : <span>{definition.horizontalLabel} horizontal · {definition.verticalLabel} vertical</span>}
        <span>Grid {visibleGridSpacing} mm · {snapEnabled
          ? view === "front" && selected?.profile_points
            ? `Outline snap ${OUTLINE_SNAP_MM} mm`
            : `Snap ${GRID_SPACING_MM} mm`
          : "Snap off"}</span>
      </footer>
    </main>
  );
}
