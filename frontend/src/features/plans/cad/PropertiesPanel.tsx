import { useEffect, useState } from "react";

import type { PlanComponent } from "../../../types/api";

interface Props {
  component: PlanComponent | null;
  locked: boolean;
  busy: boolean;
  onCommit: (before: PlanComponent, after: PlanComponent) => void;
}

type EditableKey = "component_name" | "component_type" | "x" | "y" | "z" | "width" | "height" | "depth" | "thickness" | "rotation_y" | "rotation_x" | "rotation_z" | "quantity";
type FormValues = Record<EditableKey, string>;

function valuesFor(component: PlanComponent): FormValues {
  return {
    component_name: component.component_name,
    component_type: component.component_type,
    x: component.x,
    y: component.y,
    z: component.z,
    width: component.width,
    height: component.height,
    depth: component.depth ?? "",
    thickness: component.thickness ?? "",
    rotation_y: component.rotation_y,
    rotation_x: component.rotation_x,
    rotation_z: component.rotation_z,
    quantity: String(component.quantity),
  };
}

function validNumeric(key: EditableKey, value: string): boolean {
  const number = Number(value);
  if (!Number.isFinite(number)) return false;
  if (["width", "height", "depth", "thickness", "quantity"].includes(key)) return number > 0;
  return true;
}

export function PropertiesPanel({ component, locked, busy, onCommit }: Props) {
  const [form, setForm] = useState<FormValues | null>(component ? valuesFor(component) : null);

  useEffect(() => {
    setForm(component ? valuesFor(component) : null);
  }, [component]);

  if (!component || !form) {
    return (
      <aside className="cad-properties cad-properties--empty">
        <span aria-hidden="true">⌖</span>
        <strong>No component selected</strong>
        <p>Select a part in the drawing or component tree to inspect its exact geometry.</p>
      </aside>
    );
  }
  const activeForm = form;

  function commit(key: EditableKey) {
    if (locked || busy || !form || !component) return;
    const value = form[key].trim();
    if (key === "component_name" && !value) {
      setForm(valuesFor(component));
      return;
    }
    if (key !== "component_name" && key !== "component_type" && !validNumeric(key, value)) {
      setForm(valuesFor(component));
      return;
    }
    let after: PlanComponent = {
      ...component,
      [key]: key === "quantity" ? Math.max(1, Math.round(Number(value))) : value,
    };
    if (key === "rotation_y") {
      after = { ...after, rotation: value };
    }
    if (component.profile_points && (key === "width" || key === "height")) {
      const scale = Number(value) / Number(component[key]);
      after.profile_points = component.profile_points.map((point) => ({
        ...point,
        [key === "width" ? "u" : "v"]: String(Number(point[key === "width" ? "u" : "v"]) * scale),
      }));
    }
    if (JSON.stringify(after) !== JSON.stringify(component)) onCommit(component, after);
  }

  function field(label: string, key: EditableKey, unit?: string) {
    return (
      <label className="cad-property-field">
        <span>{label}</span>
        <div>
          <input
            type={key === "component_name" ? "text" : "number"}
            step={key === "quantity" ? "1" : "any"}
            min={["width", "height", "depth", "thickness", "quantity"].includes(key) ? "0.0001" : undefined}
            value={activeForm[key]}
            disabled={locked || busy}
            onChange={(event) => setForm({ ...activeForm, [key]: event.target.value })}
            onBlur={() => commit(key)}
            onKeyDown={(event) => { if (event.key === "Enter") event.currentTarget.blur(); }}
          />
          {unit && <b>{unit}</b>}
        </div>
      </label>
    );
  }

  return (
    <aside className="cad-properties" aria-label="Selected component properties">
      <div className="cad-panel-heading">
        <div><small>Inspector</small><strong>Properties</strong></div>
        <span>{locked ? "LOCKED" : busy ? "SAVING" : "DRAFT"}</span>
      </div>
      <div className="cad-properties__body">
        <section>
          <h4>Identity</h4>
          {field("Component name", "component_name")}
          <label className="cad-property-field">
            <span>Component type</span>
            <select
              value={form.component_type}
              disabled={locked || busy}
              onChange={(event) => {
                const next = { ...form, component_type: event.target.value };
                setForm(next);
                onCommit(component, { ...component, component_type: event.target.value as PlanComponent["component_type"] });
              }}
            >
              <option value="panel">Panel</option>
              <option value="leg">Leg</option>
            </select>
          </label>
        </section>
        <section>
          <h4>Position · canonical axes</h4>
          <div className="cad-property-grid">
            {field("X · left/right", "x", "mm")}
            {field("Y · vertical", "y", "mm")}
            {field("Z · front/back", "z", "mm")}
          </div>
        </section>
        <section>
          <h4>Dimensions</h4>
          <div className="cad-property-grid">
            {field("Width · X", "width", "mm")}
            {field("Height · Y", "height", "mm")}
            {component.depth !== null && field("Depth · Z", "depth", "mm")}
            {component.thickness !== null && field("Thickness", "thickness", "mm")}
          </div>
        </section>
        <section>
          <h4>Rotation & quantity</h4>
          <div className="cad-property-grid">
            {field("Turn · Y", "rotation_y", "deg")}
            {field("Tilt · X", "rotation_x", "deg")}
            {field("Tilt · Z", "rotation_z", "deg")}
            {field("Quantity", "quantity")}
          </div>
        </section>
        {component.source_views.length > 0 && (
          <div className="cad-source-data">
            <strong>Photo source</strong>
            <span>{component.source_views.join(" · ")}</span>
            {component.source_confidence && <small>{Math.round(Number(component.source_confidence) * 100)}% source confidence</small>}
          </div>
        )}
      </div>
    </aside>
  );
}
