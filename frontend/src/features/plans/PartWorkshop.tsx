import { useRef } from "react";

import { BusyLabel } from "../../components/Feedback";
import { formatNumber } from "../../lib/format";
import type { PlanComponent } from "../../types/api";

export type EditableField =
  | "component_name"
  | "component_type"
  | "width"
  | "height"
  | "depth"
  | "thickness"
  | "x"
  | "y"
  | "z"
  | "rotation"
  | "quantity";

interface Props {
  components: PlanComponent[];
  selectedId: string | null;
  disabled: boolean;
  busy: boolean;
  dirtyIds: ReadonlySet<string>;
  onSelect: (id: string) => void;
  onChange: (id: string, field: EditableField, value: string) => void;
  onSave: (component: PlanComponent) => void;
}

interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
  maxDepth: number;
}

function planBounds(components: PlanComponent[]): Bounds {
  return {
    minX: Math.min(0, ...components.map((part) => Number(part.x))),
    minY: Math.min(0, ...components.map((part) => Number(part.y))),
    maxX: Math.max(1, ...components.map((part) => Number(part.x) + Number(part.width))),
    maxY: Math.max(1, ...components.map((part) => Number(part.y) + Number(part.height))),
    maxDepth: Math.max(1, ...components.map((part) => Number(part.z) + Number(part.depth ?? part.thickness ?? 1))),
  };
}

function FrontPreview({ components, selected, bounds }: { components: PlanComponent[]; selected: PlanComponent; bounds: Bounds }) {
  const spanX = Math.max(bounds.maxX - bounds.minX, 1);
  const spanY = Math.max(bounds.maxY - bounds.minY, 1);
  const scale = Math.min(410 / spanX, 250 / spanY);
  const transform = (part: PlanComponent) => ({
    x: 55 + (Number(part.x) - bounds.minX) * scale,
    y: 310 - (Number(part.y) - bounds.minY + Number(part.height)) * scale,
    width: Math.max(Number(part.width) * scale, 2),
    height: Math.max(Number(part.height) * scale, 2),
  });
  const active = transform(selected);

  return (
    <svg viewBox="0 0 520 350" role="img" aria-label={`Live front preview of ${selected.component_name}`}>
      <defs>
        <pattern id="part-grid-front" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" fill="none" stroke="currentColor" strokeWidth=".5" />
        </pattern>
        <marker id="arrow-front" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="currentColor" />
        </marker>
      </defs>
      <rect width="520" height="350" className="part-preview-grid" fill="url(#part-grid-front)" />
      <text x="22" y="25" className="part-preview-label">FRONT · LIVE PREVIEW</text>
      <line x1="28" y1="312" x2="492" y2="312" className="part-preview-ground" />
      {components.filter((part) => part.id !== selected.id).map((part) => {
        const shape = transform(part);
        return <rect key={part.id} {...shape} className="part-preview-ghost" />;
      })}
      <rect {...active} className={`part-preview-active part-preview-active--${selected.component_type}`} />
      <line x1={active.x} y1={Math.max(42, active.y - 18)} x2={active.x + active.width} y2={Math.max(42, active.y - 18)} className="part-measure-line" markerStart="url(#arrow-front)" markerEnd="url(#arrow-front)" />
      <text x={active.x + active.width / 2} y={Math.max(36, active.y - 24)} textAnchor="middle" className="part-measure-text">{formatNumber(selected.width, 1)} mm</text>
      <line x1={Math.max(18, active.x - 18)} y1={active.y} x2={Math.max(18, active.x - 18)} y2={active.y + active.height} className="part-measure-line" markerStart="url(#arrow-front)" markerEnd="url(#arrow-front)" />
      <text x={Math.max(12, active.x - 26)} y={active.y + active.height / 2} textAnchor="middle" className="part-measure-text" transform={`rotate(-90 ${Math.max(12, active.x - 26)} ${active.y + active.height / 2})`}>{formatNumber(selected.height, 1)} mm</text>
      <text x="260" y="338" textAnchor="middle" className="part-preview-caption">Move X/Y or change width/height to see this part update</text>
    </svg>
  );
}

function SidePreview({ selected, bounds }: { selected: PlanComponent; bounds: Bounds }) {
  const depth = Number(selected.depth ?? selected.thickness ?? 1);
  const scale = Math.min(190 / Math.max(bounds.maxDepth, depth, 1), 250 / Math.max(bounds.maxY - bounds.minY, Number(selected.height), 1));
  const width = Math.max(depth * scale, 3);
  const height = Math.max(Number(selected.height) * scale, 3);
  const x = 55 + Number(selected.z) * scale;
  const y = 310 - (Number(selected.y) - bounds.minY + Number(selected.height)) * scale;

  return (
    <svg viewBox="0 0 300 350" role="img" aria-label={`Live side preview of ${selected.component_name}`}>
      <defs>
        <pattern id="part-grid-side" width="20" height="20" patternUnits="userSpaceOnUse">
          <path d="M20 0H0V20" fill="none" stroke="currentColor" strokeWidth=".5" />
        </pattern>
        <marker id="arrow-side" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="currentColor" />
        </marker>
      </defs>
      <rect width="300" height="350" className="part-preview-grid" fill="url(#part-grid-side)" />
      <text x="22" y="25" className="part-preview-label">SIDE · DEPTH</text>
      <line x1="28" y1="312" x2="272" y2="312" className="part-preview-ground" />
      <rect x={x} y={y} width={width} height={height} className={`part-preview-active part-preview-active--${selected.component_type}`} />
      <line x1={x} y1={Math.max(42, y - 18)} x2={x + width} y2={Math.max(42, y - 18)} className="part-measure-line" markerStart="url(#arrow-side)" markerEnd="url(#arrow-side)" />
      <text x={x + width / 2} y={Math.max(36, y - 24)} textAnchor="middle" className="part-measure-text">{formatNumber(depth, 1)} mm</text>
      <text x="150" y="338" textAnchor="middle" className="part-preview-caption">Depth uses depth first, then thickness</text>
    </svg>
  );
}

function NumberControl({
  label,
  value,
  field,
  selected,
  disabled,
  min,
  max,
  hint,
  onChange,
}: {
  label: string;
  value: string;
  field: EditableField;
  selected: PlanComponent;
  disabled: boolean;
  min: number;
  max: number;
  hint: string;
  onChange: Props["onChange"];
}) {
  const numeric = Number(value || 0);
  const sliderValue = Math.min(max, Math.max(min, Number.isFinite(numeric) ? numeric : min));
  return (
    <label className="part-control">
      <span><strong>{label}</strong><small>{hint}</small></span>
      <div className="part-control__inputs">
        <input aria-label={`${selected.component_name} ${label} slider`} disabled={disabled} type="range" min={min} max={max} step="1" value={sliderValue} onChange={(event) => onChange(selected.id, field, event.target.value)} />
        <div><input aria-label={`${selected.component_name} ${label}`} disabled={disabled} type="number" min={min > 0 ? "0.0001" : undefined} step="any" value={value} onChange={(event) => onChange(selected.id, field, event.target.value)} /><b>mm</b></div>
      </div>
    </label>
  );
}

export function PartWorkshop({ components, selectedId, disabled, busy, dirtyIds, onSelect, onChange, onSave }: Props) {
  const componentKey = components.map((part) => part.id).join("|");
  const previewBaseline = useRef<{ key: string; bounds: Bounds }>({ key: componentKey, bounds: planBounds(components) });
  if (previewBaseline.current.key !== componentKey) {
    previewBaseline.current = { key: componentKey, bounds: planBounds(components) };
  }
  const selectedIndex = Math.max(0, components.findIndex((part) => part.id === selectedId));
  const selected = components[selectedIndex];
  const bounds = previewBaseline.current.bounds;
  if (!selected) return null;
  const maxWidth = Math.ceil(Math.max(100, (bounds.maxX - bounds.minX) * 2));
  const maxHeight = Math.ceil(Math.max(100, (bounds.maxY - bounds.minY) * 2));
  const maxDepth = Math.ceil(Math.max(100, bounds.maxDepth * 2));
  const depthField: EditableField = selected.depth !== null ? "depth" : "thickness";
  const depthValue = selected.depth ?? selected.thickness ?? "";
  const dirty = dirtyIds.has(selected.id);

  function move(direction: -1 | 1) {
    const next = (selectedIndex + direction + components.length) % components.length;
    onSelect(components[next].id);
  }

  return (
    <section className="part-workshop">
      <header className="part-workshop__header">
        <div><p className="eyebrow">Part-by-part workshop</p><h3>Edit one component and watch it change</h3><p>The highlighted part updates immediately. Save it, then move to the next part.</p></div>
        <div className="part-stepper"><button type="button" onClick={() => move(-1)} aria-label="Previous part">←</button><span><b>{selectedIndex + 1}</b> / {components.length}</span><button type="button" onClick={() => move(1)} aria-label="Next part">→</button></div>
      </header>

      <div className="part-workshop__body">
        <nav className="part-list" aria-label="Plan components">
          {components.map((part, index) => (
            <button key={part.id} type="button" className={`${part.id === selected.id ? "is-selected" : ""}${dirtyIds.has(part.id) ? " is-dirty" : ""}`} onClick={() => onSelect(part.id)}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              <div><strong>{part.component_name.replaceAll("_", " ")}</strong><small>{part.component_type} · {formatNumber(part.width, 0)} × {formatNumber(part.height, 0)} mm{dirtyIds.has(part.id) ? " · unsaved" : ""}</small></div>
            </button>
          ))}
        </nav>

        <div className="part-editor-main">
          <div className="part-live-views">
            <FrontPreview components={components} selected={selected} bounds={bounds} />
            <SidePreview selected={selected} bounds={bounds} />
          </div>

          <div className="part-editor-form">
            <div className="part-identity">
              <label className="field"><span>Part name</span><input disabled={disabled} value={selected.component_name} onChange={(event) => onChange(selected.id, "component_name", event.target.value)} /></label>
              <label className="field"><span>Part type</span><select disabled={disabled} value={selected.component_type} onChange={(event) => onChange(selected.id, "component_type", event.target.value)}><option value="panel">Panel</option><option value="leg">Leg</option></select></label>
            </div>
            <div className="part-control-group">
              <div className="part-control-group__title"><span>01</span><div><strong>Size</strong><small>Change the physical size of this part.</small></div></div>
              <NumberControl label="Width" hint="Left to right" value={selected.width} field="width" selected={selected} disabled={disabled} min={1} max={maxWidth} onChange={onChange} />
              <NumberControl label="Height" hint="Bottom to top" value={selected.height} field="height" selected={selected} disabled={disabled} min={1} max={maxHeight} onChange={onChange} />
              <NumberControl label={depthField === "depth" ? "Depth" : "Thickness"} hint="Front to back" value={depthValue} field={depthField} selected={selected} disabled={disabled} min={1} max={maxDepth} onChange={onChange} />
            </div>
            <div className="part-control-group">
              <div className="part-control-group__title"><span>02</span><div><strong>Position</strong><small>Move the part inside the complete piece.</small></div></div>
              <NumberControl label="X position" hint="Left / right" value={selected.x} field="x" selected={selected} disabled={disabled} min={-maxWidth} max={maxWidth * 2} onChange={onChange} />
              <NumberControl label="Y position" hint="Up / down" value={selected.y} field="y" selected={selected} disabled={disabled} min={-maxHeight} max={maxHeight * 2} onChange={onChange} />
              <NumberControl label="Z position" hint="Front / back" value={selected.z} field="z" selected={selected} disabled={disabled} min={-maxDepth} max={maxDepth * 2} onChange={onChange} />
            </div>
            <div className="part-compact-controls">
              <label className="field"><span>Rotation</span><div className="input-unit"><input disabled={disabled} type="number" step="any" value={selected.rotation} onChange={(event) => onChange(selected.id, "rotation", event.target.value)} /><b>deg</b></div></label>
              <label className="field"><span>Quantity</span><input disabled={disabled} type="number" min="1" step="1" value={selected.quantity} onChange={(event) => onChange(selected.id, "quantity", event.target.value)} /></label>
            </div>
            {!disabled && (
              <button className={`button button--wide ${dirty ? "button--primary" : "button--secondary"}`} disabled={busy || !dirty} onClick={() => onSave(selected)}>
                {busy ? <BusyLabel>Saving part…</BusyLabel> : dirty ? `Save ${selected.component_name.replaceAll("_", " ")}` : "Part is saved"}
              </button>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
