import { canOpenStep, completedSteps, workflowSteps, type WorkflowContext, type WorkflowStepId } from "../lib/workflow";

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

  return (
    <nav className="workflow-nav" aria-label="Reconstruction steps">
      {workflowSteps.map((step) => {
        const isActive = active === step.id;
        const isComplete = completed.has(step.id);
        const canVisit = canOpenStep(step.id, context);
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
