import { useEffect, useRef, useState } from "react";

import type { FurnitureDimensions, FurnitureImageCalibrationPayload, FurniturePlan, ImageView, PlanComponent } from "../../../types/api";
import { CanvasWorkspace } from "./CanvasWorkspace";
import { ComponentPanel } from "./ComponentPanel";
import { EditorToolbar } from "./EditorToolbar";
import { EditorHistory } from "./editorHistory";
import { canMutatePlan, semanticWarnings, type OrthographicView } from "./editorGeometry";
import { PropertiesPanel } from "./PropertiesPanel";
import { PartReviewGuide } from "./PartReviewGuide";
import { comparisonPhoto } from "./partReview";
import {
  initialReferenceByView,
  referenceOptionsForView,
  type ReferenceImages,
} from "./referencePhotos";

interface Props {
  plan: FurniturePlan;
  dimensions: FurnitureDimensions | null;
  components: PlanComponent[];
  referenceImages: ReferenceImages;
  busy: string | null;
  reviewMode: boolean;
  onPreview: (component: PlanComponent) => void;
  onPersist: (before: PlanComponent, after: PlanComponent) => Promise<PlanComponent | null>;
  onAdd: () => Promise<PlanComponent | null>;
  onDelete: (component: PlanComponent) => Promise<boolean>;
  onCalibrate: (view: ImageView, payload: FurnitureImageCalibrationPayload) => Promise<boolean>;
  onReview: () => void;
  onFinish: () => void;
}

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 4;

export function Furniture2DEditor({
  plan,
  dimensions,
  components,
  referenceImages,
  busy,
  reviewMode,
  onPreview,
  onPersist,
  onAdd,
  onDelete,
  onCalibrate,
  onReview,
  onFinish,
}: Props) {
  const [view, setView] = useState<OrthographicView>("front");
  const [selectedId, setSelectedId] = useState<string | null>(components[0]?.id ?? null);
  const [gridVisible, setGridVisible] = useState(true);
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [photoVisible, setPhotoVisible] = useState(reviewMode);
  const [focusSelected, setFocusSelected] = useState(false);
  const [referenceByView, setReferenceByView] = useState(() => initialReferenceByView(referenceImages));
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [, setHistoryVersion] = useState(0);
  const history = useRef(new EditorHistory<PlanComponent>(40));
  const locked = !canMutatePlan(plan.status);
  const warnings = semanticWarnings(plan.furniture_type, components);
  const selected = components.find((component) => component.id === selectedId) ?? null;
  const referenceOptions = referenceOptionsForView(view, referenceImages);
  const referenceView = referenceOptions.some((option) => option.value === referenceByView[view])
    ? referenceByView[view] : referenceOptions[0]?.value ?? null;
  const referenceImage = referenceView ? referenceImages[referenceView] : undefined;

  function refreshHistoryState() {
    setHistoryVersion((version) => version + 1);
  }

  useEffect(() => {
    setSelectedId(components[0]?.id ?? null);
    setFocusSelected(false);
    history.current.clear();
    refreshHistoryState();
  }, [plan.id, plan.status]);

  useEffect(() => {
    if (selectedId && !components.some((component) => component.id === selectedId)) {
      setSelectedId(components[0]?.id ?? null);
    }
  }, [components, selectedId]);

  function setOrthographicView(next: OrthographicView) {
    setView(next);
    setZoom(1);
    setPan({ x: 0, y: 0 });
  }

  function setReferenceView(next: ImageView) {
    setReferenceByView((current) => ({ ...current, [view]: next }));
    setPhotoVisible(true);
  }

  function compareSelected(next: OrthographicView) {
    if (!selected || busy) return;
    const photo = comparisonPhoto(next, selected, referenceImages);
    if (!photo) return;
    setOrthographicView(next);
    setReferenceByView((current) => ({ ...current, [next]: photo }));
    setPhotoVisible(true);
  }

  async function commit(before: PlanComponent, after: PlanComponent) {
    if (locked || busy || JSON.stringify(before) === JSON.stringify(after)) return;
    const saved = await onPersist(before, after);
    if (saved) {
      history.current.record({ before, after: saved });
      refreshHistoryState();
    }
  }

  async function undo() {
    if (locked || busy) return;
    const entry = history.current.undo();
    if (!entry) return;
    refreshHistoryState();
    const current = components.find((component) => component.id === entry.after.id) ?? entry.after;
    const saved = await onPersist(current, { ...entry.before, id: current.id, plan_id: current.plan_id });
    if (!saved) {
      history.current.redo();
      refreshHistoryState();
    }
  }

  async function redo() {
    if (locked || busy) return;
    const entry = history.current.redo();
    if (!entry) return;
    refreshHistoryState();
    const current = components.find((component) => component.id === entry.before.id) ?? entry.before;
    const saved = await onPersist(current, { ...entry.after, id: current.id, plan_id: current.plan_id });
    if (!saved) {
      history.current.undo();
      refreshHistoryState();
    }
  }

  async function add() {
    if (locked || busy) return;
    const created = await onAdd();
    if (created) {
      history.current.clear();
      refreshHistoryState();
      setSelectedId(created.id);
    }
  }

  async function remove(component: PlanComponent) {
    if (locked || busy) return;
    if (!window.confirm(`Delete ${component.component_name.replaceAll("_", " ")} from this draft?`)) return;
    if (await onDelete(component)) {
      history.current.clear();
      refreshHistoryState();
    }
  }

  useEffect(() => {
    function keydown(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const editingField = target?.matches("input, textarea, select, [contenteditable='true']");
      if (editingField) return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) void redo();
        else void undo();
      } else if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "y") {
        event.preventDefault();
        void redo();
      } else if (event.key === "Delete" && selected && !locked) {
        event.preventDefault();
        void remove(selected);
      } else if (event.key === "Escape") {
        setSelectedId(null);
      } else if (event.key === "+" || event.key === "=") {
        event.preventDefault();
        setZoom((value) => Math.min(MAX_ZOOM, value * 1.2));
      } else if (event.key === "-") {
        event.preventDefault();
        setZoom((value) => Math.max(MIN_ZOOM, value / 1.2));
      }
    }
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  }, [busy, components, locked, selected]);

  return (
    <div className={`furniture-cad${locked ? " is-locked" : ""}`}>
      <EditorToolbar
        view={view}
        gridVisible={gridVisible}
        snapEnabled={snapEnabled}
        photoVisible={photoVisible}
        hasPhoto={Boolean(referenceImage)}
        locked={locked}
        reviewMode={reviewMode}
        busy={Boolean(busy)}
        canUndo={history.current.canUndo}
        canRedo={history.current.canRedo}
        zoom={zoom}
        onView={setOrthographicView}
        onGrid={() => setGridVisible((visible) => !visible)}
        onSnap={() => setSnapEnabled((enabled) => !enabled)}
        onPhoto={() => setPhotoVisible((visible) => !visible)}
        onUndo={() => void undo()}
        onRedo={() => void redo()}
        onZoomIn={() => setZoom((value) => Math.min(MAX_ZOOM, value * 1.2))}
        onZoomOut={() => setZoom((value) => Math.max(MIN_ZOOM, value / 1.2))}
        onFit={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}
        onFinish={reviewMode ? onReview : onFinish}
      />
      {plan.source_reconstruction_id && (
        <PartReviewGuide
          furnitureType={plan.furniture_type}
          components={components}
          selectedId={selectedId}
          referenceImages={referenceImages}
          locked={locked}
          busy={Boolean(busy)}
          focusSelected={focusSelected}
          onSelect={setSelectedId}
          onCompare={compareSelected}
          onFocus={() => setFocusSelected((value) => !value)}
        />
      )}
      <div className="cad-editor-grid">
        <ComponentPanel
          furnitureType={plan.furniture_type}
          components={components}
          selectedId={selectedId}
          locked={locked}
          busy={Boolean(busy)}
          warnings={warnings}
          onSelect={setSelectedId}
          onAdd={() => void add()}
          onDelete={(component) => void remove(component)}
        />
        <CanvasWorkspace
          components={components}
          dimensions={dimensions}
          selectedId={selectedId}
          view={view}
          locked={locked}
          gridVisible={gridVisible}
          snapEnabled={snapEnabled}
          referenceImage={referenceImage}
          referenceView={referenceView}
          referenceOptions={referenceOptions}
          photoVisible={photoVisible}
          focusSelected={focusSelected}
          zoom={zoom}
          pan={pan}
          onPan={setPan}
          onZoom={(direction) => setZoom((value) => direction > 0 ? Math.min(MAX_ZOOM, value * 1.12) : Math.max(MIN_ZOOM, value / 1.12))}
          onReference={setReferenceView}
          onCalibration={(payload) => referenceView ? onCalibrate(referenceView, payload) : Promise.resolve(false)}
          onSelect={setSelectedId}
          onPreview={onPreview}
          onCommit={(before, after) => void commit(before, after)}
        />
        <PropertiesPanel
          component={selected}
          locked={locked}
          busy={Boolean(busy)}
          onCommit={(before, after) => void commit(before, after)}
        />
      </div>
      {locked && <div className="cad-lock-banner"><span>▣</span><strong>FINALIZED / LOCKED</strong><small>Geometry is read-only. Views, zoom, pan, and inspection remain available.</small></div>}
    </div>
  );
}
