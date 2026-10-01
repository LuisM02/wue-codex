import type {
  BomSelection,
  Furniture,
  FurnitureClassification,
  FurnitureDimensions,
  FurnitureImage,
  FurniturePlan,
  Project,
} from "../types/api";

export type WorkflowStepId = "project" | "photos" | "dimensions" | "plan" | "model" | "bom" | "estimate";

export interface WorkflowContext {
  project: Project | null;
  furniture: Furniture | null;
  classification: FurnitureClassification | null;
  images: FurnitureImage[];
  dimensions: FurnitureDimensions | null;
  plan: FurniturePlan | null;
  bomSelection: BomSelection | null;
}

export const workflowSteps: Array<{ id: WorkflowStepId; number: string; label: string; hint: string }> = [
  { id: "project", number: "01", label: "Piece", hint: "Choose the work" },
  { id: "photos", number: "02", label: "Photos", hint: "Capture five views" },
  { id: "dimensions", number: "03", label: "Measure", hint: "Set overall size" },
  { id: "plan", number: "04", label: "Plan", hint: "Review the parts" },
  { id: "model", number: "05", label: "Preview", hint: "Inspect in 3D" },
  { id: "bom", number: "06", label: "BOM", hint: "Review materials" },
  { id: "estimate", number: "07", label: "Quote", hint: "Price the build" },
];

export function hasRecognizedPhotos(context: Pick<WorkflowContext, "images" | "furniture" | "classification">): boolean {
  const views = new Set(context.images.map((image) => image.view));
  return ["front", "back", "left", "right", "top"].every((view) => views.has(view as FurnitureImage["view"]))
    && context.images.length === 5 && Boolean(context.classification)
    && context.classification?.furniture_id === context.furniture?.id
    && context.classification?.predicted_type === context.furniture?.furniture_type;
}

export function completedSteps(context: WorkflowContext): Set<WorkflowStepId> {
  const completed = new Set<WorkflowStepId>();
  if (context.project && context.furniture) completed.add("project");
  if (hasRecognizedPhotos(context)) completed.add("photos");
  if (context.dimensions) completed.add("dimensions");
  if (context.plan?.status === "finalized") {
    completed.add("plan");
    completed.add("model");
  }
  if (context.bomSelection) completed.add("bom");
  return completed;
}

export function canOpenStep(step: WorkflowStepId, context: WorkflowContext): boolean {
  if (step === "project") return true;
  if (!context.project || !context.furniture) return false;
  if (step === "photos") return true;
  if (step === "dimensions") return hasRecognizedPhotos(context);
  // Preserve inspection of historical saved designs; new analysis still has
  // a server-side current-recognition gate. Do not erase a finalized demo.
  if (step === "plan") return Boolean(context.plan) || Boolean(context.dimensions && hasRecognizedPhotos(context));
  if (step === "model" || step === "bom") return context.plan?.status === "finalized";
  return context.plan?.status === "finalized" && Boolean(context.bomSelection);
}

export function nextStep(current: WorkflowStepId, context: WorkflowContext): WorkflowStepId {
  const index = workflowSteps.findIndex(({ id }) => id === current);
  for (let next = index + 1; next < workflowSteps.length; next += 1) {
    if (canOpenStep(workflowSteps[next].id, context)) return workflowSteps[next].id;
  }
  return current;
}
