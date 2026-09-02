import { completedSteps, workflowSteps, type WorkflowContext, type WorkflowStepId } from "../lib/workflow";

export function WorkflowNav({
  active,
  context,
  onSelect,
}: {
  active: WorkflowStepId;
  context: WorkflowContext;
  onSelect: (step: WorkflowStepId) => void;
}) {
  const completed = completedSteps(context);
  const furniture = context.furniture;

  return (
    <nav className="workflow-nav" aria-label="Reconstruction steps">
      {workflowSteps.map((step) => {
        const isActive = active === step.id;
        const isComplete = completed.has(step.id);
        const canVisit = step.id === "project" || Boolean(furniture) && (
          step.id === "photos" ||
          (step.id === "dimensions" && context.images.length === 5 && Boolean(furniture?.furniture_type)) ||
          (step.id === "plan" && Boolean(context.dimensions)) ||
          ((step.id === "model" || step.id === "estimate") && context.plan?.status === "finalized")
        );
        return (
          <button
            key={step.id}
            type="button"
            className={`workflow-nav__item${isActive ? " is-active" : ""}${isComplete ? " is-complete" : ""}`}
            disabled={!canVisit}
            onClick={() => onSelect(step.id)}
            aria-current={isActive ? "step" : undefined}
          >
            <span className="workflow-nav__number">{isComplete ? "✓" : step.number}</span>
            <span>
              <strong>{step.label}</strong>
              <small>{step.hint}</small>
            </span>
          </button>
        );
      })}
    </nav>
  );
}
