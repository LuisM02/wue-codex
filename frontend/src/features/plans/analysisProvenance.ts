import type { FurniturePlan, FurnitureReconstruction, PlanComponent, ReconstructionPart } from "../../types/api";

type AnalysisSource = Pick<FurnitureReconstruction, "id" | "furniture_id" | "furniture_type"> & {
  parts: Array<Pick<ReconstructionPart, "id">>;
};
type PlanSource = Pick<FurniturePlan, "source_reconstruction_id" | "furniture_id" | "furniture_type"> & {
  components: Array<Pick<PlanComponent, "source_reconstruction_part_id" | "source_confidence" | "source_views">>;
};

export function analysisMatchesPlan(analysis: AnalysisSource, plan: PlanSource | null): boolean {
  if (!plan) return true; // A proposal can be shown before the first drawing exists.
  if (plan.source_reconstruction_id !== analysis.id
    || plan.furniture_id !== analysis.furniture_id
    || plan.furniture_type !== analysis.furniture_type) return false;

  // Re-analysis reuses its record ID but replaces part IDs. Deleted source
  // parts can leave null links with retained confidence/views in older plans.
  const sourced = plan.components.filter((component) =>
    component.source_reconstruction_part_id !== null
    || component.source_confidence !== null
    || component.source_views.length > 0,
  );
  const available = new Set(analysis.parts.map((part) => part.id));
  return sourced.length > 0 && sourced.every((component) =>
    component.source_reconstruction_part_id !== null
    && available.has(component.source_reconstruction_part_id),
  );
}
