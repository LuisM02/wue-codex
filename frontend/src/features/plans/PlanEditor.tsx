import { useEffect, useMemo, useState } from "react";

import { BusyLabel, EmptyState, Notice, SectionHeading } from "../../components/Feedback";
import { formatNumber, furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { Furniture, FurniturePlan, PlanComponent } from "../../types/api";
import { PartWorkshop, type EditableField } from "./PartWorkshop";

interface Props {
  furniture: Furniture;
  plan: FurniturePlan | null;
  frontImageUrl?: string;
  onPlan: (plan: FurniturePlan) => void;
  onContinue: () => void;
}

function PlanDrawing({
  components,
  selectedId,
  frontImageUrl,
  showReference,
  onSelect,
}: {
  components: PlanComponent[];
  selectedId: string | null;
  frontImageUrl?: string;
  showReference: boolean;
  onSelect: (id: string) => void;
}) {
  const shapes = useMemo(() => {
    if (!components.length) return [];
    const raw = components.map((component) => ({
      id: component.id,
      name: component.component_name,
      type: component.component_type,
      x: Number(component.x),
      y: Number(component.y),
      width: Number(component.width),
      height: Number(component.height),
    }));
    const minX = Math.min(...raw.map((shape) => shape.x));
    const minY = Math.min(...raw.map((shape) => shape.y));
    const maxX = Math.max(...raw.map((shape) => shape.x + shape.width));
    const maxY = Math.max(...raw.map((shape) => shape.y + shape.height));
    const scale = Math.min(610 / Math.max(maxX - minX, 1), 340 / Math.max(maxY - minY, 1));
    return raw.map((shape) => ({
      ...shape,
      x: 55 + (shape.x - minX) * scale,
      y: 370 - (shape.y - minY + shape.height) * scale,
      width: Math.max(shape.width * scale, 2),
      height: Math.max(shape.height * scale, 2),
    }));
  }, [components]);

  return (
    <svg viewBox="0 0 720 420" role="img" aria-label="Front elevation of the generated furniture plan">
      <defs>
        <pattern id="plan-grid" width="24" height="24" patternUnits="userSpaceOnUse">
          <path d="M 24 0 L 0 0 0 24" fill="none" stroke="currentColor" strokeWidth="0.5" />
        </pattern>
      </defs>
      <rect className="plan-grid" width="720" height="420" fill="url(#plan-grid)" />
      {frontImageUrl && showReference && (
        <image href={frontImageUrl} x="0" y="0" width="720" height="420" preserveAspectRatio="xMidYMid slice" className="plan-reference-image" />
      )}
      <line className="plan-ground" x1="28" y1="372" x2="692" y2="372" />
      {shapes.map((shape) => (
        <g key={shape.id}>
          <rect
            className={`plan-shape plan-shape--${shape.type}${selectedId === shape.id ? " is-selected" : ""}`}
            x={shape.x}
            y={shape.y}
            width={shape.width}
            height={shape.height}
            rx="2"
            tabIndex={0}
            role="button"
            aria-label={`Edit ${shape.name}`}
            onClick={() => onSelect(shape.id)}
            onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") onSelect(shape.id); }}
          />
          {shape.width > 56 && shape.height > 22 && (
            <text x={shape.x + shape.width / 2} y={shape.y + shape.height / 2 + 4} textAnchor="middle">
              {shape.name}
            </text>
          )}
        </g>
      ))}
      <text className="plan-view-label" x="32" y="32">FRONT ELEVATION · MM</text>
    </svg>
  );
}

export function PlanEditor({ furniture, plan, frontImageUrl, onPlan, onContinue }: Props) {
  const [components, setComponents] = useState<PlanComponent[]>(plan?.components ?? []);
  const [selectedId, setSelectedId] = useState<string | null>(plan?.components[0]?.id ?? null);
  const [dirtyIds, setDirtyIds] = useState<Set<string>>(new Set());
  const [showReference, setShowReference] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setComponents(plan?.components ?? []);
    setSelectedId(plan?.components[0]?.id ?? null);
    setDirtyIds(new Set());
  }, [plan?.id]);

  async function generate() {
    setBusy("generate");
    setError(null);
    try {
      onPlan(await api.plans.generate(furniture.id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function edit(id: string, field: EditableField, value: string) {
    setComponents((items) => items.map((item) => item.id === id ? {
      ...item,
      [field]: field === "quantity" ? Number(value) : value,
    } : item));
    setDirtyIds((items) => new Set(items).add(id));
  }

  async function saveComponent(component: PlanComponent) {
    if (!plan) return;
    setBusy(component.id);
    setError(null);
    try {
      const payload = {
        component_name: component.component_name,
        component_type: component.component_type,
        width: component.width,
        height: component.height,
        depth: component.depth,
        thickness: component.thickness,
        x: component.x,
        y: component.y,
        z: component.z,
        rotation: component.rotation,
        quantity: component.quantity,
      };
      const saved = await api.plans.updateComponent(plan.id, component.id, payload);
      const next = components.map((item) => item.id === saved.id ? saved : item);
      setComponents(next);
      setDirtyIds((items) => {
        const updated = new Set(items);
        updated.delete(saved.id);
        return updated;
      });
      onPlan({ ...plan, components: next });
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function finalize() {
    if (!plan) return;
    if (dirtyIds.size > 0) {
      setError(`Save ${dirtyIds.size === 1 ? "the edited part" : `all ${dirtyIds.size} edited parts`} before finalizing the plan.`);
      return;
    }
    setBusy("finalize");
    setError(null);
    try {
      onPlan(await api.plans.finalize(plan.id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function revise() {
    if (!plan) return;
    setBusy("revise");
    setError(null);
    try {
      onPlan(await api.plans.revise(plan.id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="workspace-section workspace-section--wide">
      <SectionHeading eyebrow="Step 04 · Parametric drawing" title="Review the generated parts">
        {plan && <span className={`status-badge status-badge--${plan.status}`}>Revision {plan.revision} · {plan.status}</span>}
      </SectionHeading>
      <p className="section-intro">
        The draft starts from the classified {plan ? furnitureLabel(plan.furniture_type).toLowerCase() : "furniture"} structure. Select one part at a time and compare it with the photographs before locking the revision.
      </p>
      {error && <Notice tone="danger">{error}</Notice>}

      {!plan ? (
        <div className="panel plan-empty">
          <EmptyState title="No drawing generated yet">
            WUE will create a deterministic set of panels and legs from your saved dimensions.
          </EmptyState>
          <button className="button button--primary" onClick={generate} disabled={busy === "generate"}>
            {busy === "generate" ? <BusyLabel>Drawing…</BusyLabel> : "Generate plan"}
          </button>
        </div>
      ) : (
        <>
          <div className="plan-layout">
            <div className="plan-canvas">
              {frontImageUrl && (
                <div className="plan-canvas__toolbar">
                  <span>Photo overlay is a visual guide, not a measured trace.</span>
                  <button type="button" onClick={() => setShowReference((visible) => !visible)}>
                    {showReference ? "Hide front photo" : "Show front photo"}
                  </button>
                </div>
              )}
              <PlanDrawing
                components={components}
                selectedId={selectedId}
                frontImageUrl={frontImageUrl}
                showReference={showReference}
                onSelect={setSelectedId}
              />
              <div className="plan-legend"><span><i className="legend-panel" /> Panel</span><span><i className="legend-leg" /> Leg</span></div>
            </div>
            <aside className="plan-summary panel">
              <small>Plan summary</small>
              <strong>{components.length} unique parts</strong>
              <dl>
                <div><dt>Total pieces</dt><dd>{components.reduce((sum, item) => sum + item.quantity, 0)}</dd></div>
                <div><dt>Panels</dt><dd>{components.filter((item) => item.component_type === "panel").reduce((sum, item) => sum + item.quantity, 0)}</dd></div>
                <div><dt>Legs</dt><dd>{components.filter((item) => item.component_type === "leg").reduce((sum, item) => sum + item.quantity, 0)}</dd></div>
              </dl>
              {plan.status === "draft" ? (
                <Notice tone={dirtyIds.size ? "danger" : "warning"}>
                  {dirtyIds.size
                    ? `${dirtyIds.size} part${dirtyIds.size === 1 ? " has" : "s have"} unsaved changes.`
                    : "Select a part below to edit it. A finalized plan cannot be changed."}
                </Notice>
              ) : (
                <Notice tone="success">This revision is locked and ready for reconstruction and costing.</Notice>
              )}
            </aside>
          </div>

          <PartWorkshop
            components={components}
            selectedId={selectedId}
            disabled={plan.status !== "draft"}
            busy={busy === selectedId}
            dirtyIds={dirtyIds}
            onSelect={setSelectedId}
            onChange={edit}
            onSave={saveComponent}
          />

          <details className="component-schedule">
            <summary><div><strong>Full component schedule</strong><small>Exact saved values for every part</small></div><span>Show table</span></summary>
            <div className="component-table-wrap">
              <table className="component-table">
                <thead><tr><th>Part</th><th>Type</th><th>Width</th><th>Height</th><th>Depth</th><th>Thick.</th><th>X</th><th>Y</th><th>Z</th><th>Qty.</th></tr></thead>
                <tbody>
                  {components.map((component) => (
                    <tr key={component.id} className={component.id === selectedId ? "is-selected" : undefined} onClick={() => setSelectedId(component.id)}>
                      <td>{component.component_name.replaceAll("_", " ")}</td>
                      <td>{component.component_type}</td>
                      {(["width", "height", "depth", "thickness", "x", "y", "z"] as const).map((field) => (
                        <td key={field}>{component[field] === null ? "—" : formatNumber(component[field] as string, 1)}</td>
                      ))}
                      <td>{component.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          <div className="section-footer">
            <div><small>Current plan</small><strong>Revision {plan.revision} · {formatNumber(components.length, 0)} component definitions</strong></div>
            {plan.status === "draft" ? (
              <button className="button button--primary" onClick={finalize} disabled={Boolean(busy) || dirtyIds.size > 0}>{busy === "finalize" ? <BusyLabel>Validating…</BusyLabel> : dirtyIds.size ? "Save edited parts first" : "Finalize plan"}</button>
            ) : (
              <div className="button-row">
                <button className="button button--secondary" onClick={revise} disabled={Boolean(busy)}>{busy === "revise" ? <BusyLabel>Copying…</BusyLabel> : "Create editable revision"}</button>
                <button className="button button--primary" onClick={onContinue}>View 3D model <span>→</span></button>
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}
