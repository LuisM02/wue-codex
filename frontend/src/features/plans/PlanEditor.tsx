import { useEffect, useState } from "react";

import { BusyLabel, EmptyState, Notice, SectionHeading } from "../../components/Feedback";
import { furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { Furniture, FurniturePlan, PlanComponent, PlanComponentPayload } from "../../types/api";
import { Furniture2DEditor } from "./cad/Furniture2DEditor";
import { nextShelfName } from "./cad/editorGeometry";

interface Props {
  furniture: Furniture;
  plan: FurniturePlan | null;
  frontImageUrl?: string;
  onPlan: (plan: FurniturePlan) => void;
  onContinue: () => void;
}

function componentPayload(component: PlanComponent): PlanComponentPayload {
  return {
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
    rotation_x: component.rotation_x,
    rotation_y: component.rotation_y,
    rotation_z: component.rotation_z,
    geometry_kind: component.geometry_kind,
    profile_points: component.profile_points,
    quantity: component.quantity,
    sort_order: component.sort_order,
  };
}

function nextLegName(components: PlanComponent[]): string {
  const names = new Set(components.map((component) => component.component_name));
  let number = 1;
  while (names.has(`leg_${number}`)) number += 1;
  return `leg_${number}`;
}

function addedPartPayload(plan: FurniturePlan, components: PlanComponent[]): PlanComponentPayload {
  const shelf = plan.furniture_type === "bookshelf";
  const source = shelf
    ? components.find((component) => /^shelf_[1-9]\d*$/.test(component.component_name))
      ?? components.find((component) => component.component_name === "bottom_panel")
    : components.find((component) => component.component_type === "leg");
  const fallback: PlanComponentPayload = shelf
    ? {
        component_name: nextShelfName(components), component_type: "panel", width: "500", height: "25", depth: "300", thickness: null,
        x: "0", y: "100", z: "0", rotation: "0", rotation_x: "0", rotation_y: "0", rotation_z: "0",
        geometry_kind: "box", profile_points: null, quantity: 1, sort_order: components.length,
      }
    : {
        component_name: nextLegName(components), component_type: "leg", width: "40", height: "400", depth: "40", thickness: null,
        x: "0", y: "0", z: "0", rotation: "0", rotation_x: "0", rotation_y: "0", rotation_z: "0",
        geometry_kind: "box", profile_points: null, quantity: 1, sort_order: components.length,
      };
  if (!source) return fallback;
  const payload = componentPayload(source);
  return {
    ...payload,
    component_name: shelf ? nextShelfName(components) : nextLegName(components),
    component_type: shelf ? "panel" : "leg",
    x: shelf ? source.x : String(Number(source.x) + Number(source.width) + 25),
    y: shelf ? String(Number(source.y) + Number(source.height) + 25) : source.y,
    profile_points: source.profile_points?.map((point) => ({ ...point })) ?? null,
    sort_order: Math.max(-1, ...components.map((component) => component.sort_order)) + 1,
  };
}

export function PlanEditor({ furniture, plan, frontImageUrl, onPlan, onContinue }: Props) {
  const [components, setComponents] = useState<PlanComponent[]>(plan?.components ?? []);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const isPhotoDerived = Boolean(plan?.source_reconstruction_id);
  const reviewRequired = Boolean(
    plan?.status === "draft" && isPhotoDerived && !plan.parts_reviewed_at,
  );

  useEffect(() => {
    setComponents(plan?.components ?? []);
  }, [plan?.id, plan?.status]);

  async function generate() {
    setBusy("generate");
    setError(null);
    try {
      await api.reconstruction.run(furniture.id);
      onPlan(await api.plans.generate(furniture.id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  function replaceComponent(component: PlanComponent) {
    setComponents((items) => items.map((item) => item.id === component.id ? component : item));
  }

  async function persistComponent(before: PlanComponent, after: PlanComponent): Promise<PlanComponent | null> {
    if (!plan || plan.status !== "draft") return null;
    replaceComponent(after);
    setBusy(`component:${after.id}`);
    setError(null);
    try {
      const saved = await api.plans.updateComponent(plan.id, after.id, componentPayload(after));
      const next = components.map((item) => item.id === saved.id ? saved : item);
      setComponents(next);
      onPlan({ ...plan, components: next });
      return saved;
    } catch (reason) {
      replaceComponent(before);
      setError(`${(reason as Error).message} The last edit was restored.`);
      try {
        const authoritative = await api.plans.get(plan.id);
        setComponents(authoritative.components);
        onPlan(authoritative);
      } catch {
        // Keep the known pre-edit value when the server cannot be reloaded.
      }
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function addComponent(): Promise<PlanComponent | null> {
    if (!plan || plan.status !== "draft") return null;
    setBusy("add");
    setError(null);
    try {
      const created = await api.plans.addComponent(plan.id, addedPartPayload(plan, components));
      const next = [...components, created].sort((first, second) => first.sort_order - second.sort_order);
      setComponents(next);
      onPlan({ ...plan, components: next });
      return created;
    } catch (reason) {
      setError((reason as Error).message);
      return null;
    } finally {
      setBusy(null);
    }
  }

  async function deleteComponent(component: PlanComponent): Promise<boolean> {
    if (!plan || plan.status !== "draft") return false;
    setBusy(`delete:${component.id}`);
    setError(null);
    try {
      await api.plans.deleteComponent(plan.id, component.id);
      const next = components.filter((item) => item.id !== component.id);
      setComponents(next);
      onPlan({ ...plan, components: next });
      return true;
    } catch (reason) {
      setError((reason as Error).message);
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function finalize() {
    if (!plan || plan.status !== "draft") return;
    setBusy("finalize");
    setError(null);
    try {
      const finalized = await api.plans.finalize(plan.id);
      setComponents(finalized.components);
      onPlan(finalized);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function reviewParts() {
    if (!plan || plan.status !== "draft") return;
    setBusy("review");
    setError(null);
    try {
      const reviewed = await api.plans.reviewParts(plan.id);
      setComponents(reviewed.components);
      onPlan(reviewed);
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

  async function rebuildFromPhotos() {
    if (!plan) return;
    setBusy("rebuild");
    setError(null);
    try {
      await api.reconstruction.run(furniture.id);
      onPlan(await api.plans.rebuildFromPhotos(plan.id));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="workspace-section workspace-section--wide workspace-section--cad">
      <SectionHeading eyebrow="Step 04 · Parametric CAD" title={plan ? "Furniture 2D editor" : "Build the 2D furniture model"}>
        {plan && <span className={`status-badge status-badge--${plan.status}`}>Revision {plan.revision} · {plan.status}</span>}
      </SectionHeading>
      <p className="section-intro">
        {plan && !isPhotoDerived
          ? plan.status === "finalized"
            ? "This legacy revision was created before photo-derived reconstruction. It is read-only and is not a copy of the photographed design."
            : "This legacy revision was created before photo-derived reconstruction. It remains editable, but it is not a copy of the photographed design."
          : `WUE uses canonical X/Y/Z component geometry. Edit the reconstructed ${plan ? furnitureLabel(plan.furniture_type).toLowerCase() : "furniture"} in Front, Side, and Top views, then finish the revision to lock it for 3D and costing.`}
      </p>
      {error && <Notice tone="danger">{error}</Notice>}
      {reviewRequired && (
        <Notice tone="warning">
          <strong>Review the AI-detected parts before finalizing.</strong>{" "}
          Compare the highlighted parts with the front photograph, rename or resize incorrect parts,
          add anything missing, and remove false detections. Confirming records your review; it does not finalize the plan.
        </Notice>
      )}

      {!plan ? (
        <div className="panel plan-empty">
          <EmptyState title="No photo-derived drawing yet">
            WUE will analyze all five photographs and create editable components from their visible outlines. It will not substitute a standard furniture template.
          </EmptyState>
          <button className="button button--primary" onClick={generate} disabled={busy === "generate"}>
            {busy === "generate" ? <BusyLabel>Analyzing photos…</BusyLabel> : "Analyze photos & build 2D parts"}
          </button>
        </div>
      ) : (
        <>
          <Furniture2DEditor
            plan={plan}
            components={components}
            frontImageUrl={frontImageUrl}
            busy={busy}
            reviewMode={reviewRequired}
            onPreview={replaceComponent}
            onPersist={persistComponent}
            onAdd={addComponent}
            onDelete={deleteComponent}
            onReview={() => void reviewParts()}
            onFinish={() => void finalize()}
          />
          <div className="section-footer cad-section-footer">
            <div>
              <small>Revision {plan.revision}</small>
              <strong>{plan.status === "draft"
                ? reviewRequired
                  ? "AI proposal · user review required"
                  : "Editable 2D source of truth"
                : "Locked for deterministic 3D and estimates"}</strong>
            </div>
            {plan.status === "finalized" && (
              <div className="button-row">
                <button className="button button--secondary" onClick={rebuildFromPhotos} disabled={Boolean(busy)}>{busy === "rebuild" ? <BusyLabel>Analyzing…</BusyLabel> : "Rebuild from photos"}</button>
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
