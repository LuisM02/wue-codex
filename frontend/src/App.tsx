import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import { BusyLabel, Notice } from "./components/Feedback";
import { WorkflowNav } from "./components/WorkflowNav";
import { DimensionsForm } from "./features/dimensions/DimensionsForm";
import { EstimatePanel } from "./features/estimates/EstimatePanel";
import { ImageWorkspace } from "./features/images/ImageWorkspace";
import { PlanEditor } from "./features/plans/PlanEditor";
import { ProjectSetup } from "./features/projects/ProjectSetup";
import { furnitureLabel } from "./lib/format";
import { canOpenStep, type WorkflowContext, type WorkflowStepId } from "./lib/workflow";
import { api } from "./services/apiClient";
import type {
  Furniture,
  FurnitureClassification,
  FurnitureDimensions,
  FurnitureImage,
  FurniturePlan,
  Project,
} from "./types/api";

const FurnitureViewer = lazy(() =>
  import("./features/viewer/FurnitureViewer").then((module) => ({
    default: module.FurnitureViewer,
  })),
);

export default function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [furniture, setFurniture] = useState<Furniture | null>(null);
  const [images, setImages] = useState<FurnitureImage[]>([]);
  const [classification, setClassification] = useState<FurnitureClassification | null>(null);
  const [dimensions, setDimensions] = useState<FurnitureDimensions | null>(null);
  const [plan, setPlan] = useState<FurniturePlan | null>(null);
  const [step, setStep] = useState<WorkflowStepId>("project");
  const [loading, setLoading] = useState(true);
  const [loadingPiece, setLoadingPiece] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    api.projects.list()
      .then((items) => { if (current) setProjects(items); })
      .catch((reason: Error) => { if (current) setError(reason.message); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, []);

  useEffect(() => {
    setImages([]);
    setClassification(null);
    setDimensions(null);
    setPlan(null);
    if (!furniture) return;
    let current = true;
    setLoadingPiece(true);
    Promise.allSettled([
      api.images.list(furniture.id),
      api.classification.get(furniture.id),
      api.dimensions.get(furniture.id),
      api.plans.list(furniture.id),
    ]).then(([imageResult, classificationResult, dimensionsResult, planResult]) => {
      if (!current) return;
      if (imageResult.status === "fulfilled") setImages(imageResult.value);
      if (classificationResult.status === "fulfilled") setClassification(classificationResult.value);
      if (dimensionsResult.status === "fulfilled") setDimensions(dimensionsResult.value);
      if (planResult.status === "fulfilled" && planResult.value.length) {
        const ordered = [...planResult.value].sort((a, b) => b.revision - a.revision);
        setPlan(ordered.find((item) => item.status === "draft") ?? ordered[0]);
      }
    }).finally(() => {
      if (current) setLoadingPiece(false);
    });
    return () => { current = false; };
  }, [furniture]);

  const context = useMemo<WorkflowContext>(() => ({
    project,
    furniture,
    images,
    dimensions,
    plan,
  }), [project, furniture, images, dimensions, plan]);

  function changeProject(value: Project | null) {
    setProject(value);
    setFurniture(null);
    setStep("project");
  }

  function changeFurniture(value: Furniture | null) {
    setFurniture(value);
    setStep("project");
  }

  function visit(next: WorkflowStepId) {
    if (canOpenStep(next, context)) setStep(next);
  }

  if (loading) {
    return (
      <main className="app-loading">
        <div className="brand brand--loading"><span className="brand__mark">W</span><strong>WUE</strong></div>
        <BusyLabel>Opening the workshop…</BusyLabel>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="brand" type="button" onClick={() => setStep("project")} aria-label="WUE home">
          <span className="brand__mark">W</span>
          <span><strong>WUE</strong><small>Furniture workshop</small></span>
        </button>
        <div className="topbar__context">
          {project ? (
            <>
              <span><small>Project</small><strong>{project.name}</strong></span>
              {furniture && <i aria-hidden="true">/</i>}
              {furniture && <span><small>Piece</small><strong>{furniture.name}</strong></span>}
            </>
          ) : (
            <span className="topbar__welcome">New reconstruction workspace</span>
          )}
        </div>
        {furniture && (
          <div className="topbar__piece">
            <span className={`furniture-glyph furniture-glyph--${furniture.furniture_type}`} aria-hidden="true" />
            <div><small>Type</small><strong>{furnitureLabel(furniture.furniture_type)}</strong></div>
          </div>
        )}
      </header>

      <aside className="sidebar">
        <div className="sidebar__intro"><p className="eyebrow">Build path</p><strong>From reference to quote</strong></div>
        <WorkflowNav active={step} context={context} onSelect={visit} />
        <div className="sidebar__note">
          <span aria-hidden="true">i</span>
          <p><strong>One clear source</strong>Your photos, measurements, plan, model, and quote remain connected.</p>
        </div>
      </aside>

      <main className="main-workspace">
        {error && <Notice tone="danger">Could not load projects: {error}</Notice>}
        {loadingPiece && <div className="piece-loading"><BusyLabel>Loading saved work…</BusyLabel></div>}

        {step === "project" && (
          <ProjectSetup
            projects={projects}
            project={project}
            furniture={furniture}
            onProject={changeProject}
            onFurniture={changeFurniture}
            onProjectsChanged={setProjects}
            onContinue={() => visit("photos")}
          />
        )}
        {step === "photos" && furniture && (
          <ImageWorkspace
            furniture={furniture}
            images={images}
            classification={classification}
            onImages={setImages}
            onClassification={setClassification}
            onContinue={() => visit("dimensions")}
          />
        )}
        {step === "dimensions" && furniture && (
          <DimensionsForm
            furniture={furniture}
            dimensions={dimensions}
            onDimensions={setDimensions}
            onContinue={() => visit("plan")}
          />
        )}
        {step === "plan" && furniture && (
          <PlanEditor
            furniture={furniture}
            plan={plan}
            onPlan={setPlan}
            onContinue={() => visit("model")}
          />
        )}
        {step === "model" && furniture && plan?.status === "finalized" && (
          <Suspense fallback={<div className="piece-loading"><BusyLabel>Opening 3D studio…</BusyLabel></div>}>
            <FurnitureViewer furniture={furniture} plan={plan} onContinue={() => visit("estimate")} />
          </Suspense>
        )}
        {step === "estimate" && furniture && plan?.status === "finalized" && (
          <EstimatePanel furniture={furniture} plan={plan} />
        )}
      </main>
    </div>
  );
}
