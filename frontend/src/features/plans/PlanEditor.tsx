import { useEffect, useMemo, useState } from "react";

import { BusyLabel, EmptyState, Notice, SectionHeading } from "../../components/Feedback";
import { formatNumber, furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { Furniture, FurniturePlan, PlanComponent } from "../../types/api";

type EditableField = "component_name" | "component_type" | "width" | "height" | "depth" | "thickness" | "x" | "y" | "z" | "rotation" | "quantity";

interface Props {
  furniture: Furniture;
  plan: FurniturePlan | null;
  onPlan: (plan: FurniturePlan) => void;
  onContinue: () => void;
}

function PlanDrawing({ components }: { components: PlanComponent[] }) {
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
      <line className="plan-ground" x1="28" y1="372" x2="692" y2="372" />
      {shapes.map((shape) => (
        <g key={shape.id}>
          <rect
            className={`plan-shape plan-shape--${shape.type}`}
            x={shape.x}
            y={shape.y}
            width={shape.width}
            height={shape.height}
            rx="2"
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

export function PlanEditor({ furniture, plan, onPlan, onContinue }: Props) {
  const [components, setComponents] = useState<PlanComponent[]>(plan?.components ?? []);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => setComponents(plan?.components ?? []), [plan]);

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
      onPlan({ ...plan, components: next });
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function finalize() {
    if (!plan) return;
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
        The plan is generated from the overall measurements using fixed rules for a {furnitureLabel(furniture.furniture_type).toLowerCase()}. Adjust a part before locking the revision.
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
              <PlanDrawing components={components} />
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
                <Notice tone="warning">Save any edited rows before finalizing. A finalized plan cannot be changed.</Notice>
              ) : (
                <Notice tone="success">This revision is locked and ready for reconstruction and costing.</Notice>
              )}
            </aside>
          </div>

          <div className="component-table-wrap">
            <div className="component-table__heading"><div><h3>Component schedule</h3><p>All dimensions and positions are in millimeters.</p></div></div>
            <table className="component-table">
              <thead><tr><th>Part</th><th>Type</th><th>Width</th><th>Height</th><th>Depth</th><th>Thick.</th><th>X</th><th>Y</th><th>Z</th><th>Qty.</th>{plan.status === "draft" && <th />}</tr></thead>
              <tbody>
                {components.map((component) => (
                  <tr key={component.id}>
                    <td><input aria-label="Part name" disabled={plan.status !== "draft"} value={component.component_name} onChange={(e) => edit(component.id, "component_name", e.target.value)} /></td>
                    <td><select aria-label="Part type" disabled={plan.status !== "draft"} value={component.component_type} onChange={(e) => edit(component.id, "component_type", e.target.value)}><option value="panel">Panel</option><option value="leg">Leg</option></select></td>
                    {(["width", "height", "depth", "thickness", "x", "y", "z"] as EditableField[]).map((field) => (
                      <td key={field}><input aria-label={field} disabled={plan.status !== "draft"} type="number" step="any" min={["width", "height", "depth", "thickness"].includes(field) ? "0.0001" : undefined} value={(component[field as keyof PlanComponent] as string | null) ?? ""} onChange={(e) => edit(component.id, field, e.target.value)} /></td>
                    ))}
                    <td><input aria-label="Quantity" disabled={plan.status !== "draft"} type="number" min="1" step="1" value={component.quantity} onChange={(e) => edit(component.id, "quantity", e.target.value)} /></td>
                    {plan.status === "draft" && <td><button className="table-save" onClick={() => saveComponent(component)} disabled={busy === component.id}>{busy === component.id ? "…" : "Save"}</button></td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="section-footer">
            <div><small>Current plan</small><strong>Revision {plan.revision} · {formatNumber(components.length, 0)} component definitions</strong></div>
            {plan.status === "draft" ? (
              <button className="button button--primary" onClick={finalize} disabled={Boolean(busy)}>{busy === "finalize" ? <BusyLabel>Validating…</BusyLabel> : "Finalize plan"}</button>
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
