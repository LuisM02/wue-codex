import type {
  BomSelection,
  Furniture,
  FurnitureDimensions,
  FurnitureImage,
  FurniturePlan,
  Project,
} from "../types/api";

export type WorkflowStepId = "project" | "photos" | "dimensions" | "plan" | "model" | "bom" | "estimate";

export interface WorkflowContext {
  project: Project | null;
  furniture: Furniture | null;
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

export function completedSteps(context: WorkflowContext): Set<WorkflowStepId> {
  const completed = new Set<WorkflowStepId>();
  if (context.project && context.furniture) completed.add("project");
  if (context.images.length === 5 && context.furniture?.furniture_type) completed.add("photos");
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
  if (step === "dimensions") return context.images.length === 5 && Boolean(context.furniture.furniture_type);
  if (step === "plan") return Boolean(context.dimensions);
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
