import type { FurnitureType, PlanComponent } from "../../../types/api";

interface Props {
  furnitureType: FurnitureType;
  components: PlanComponent[];
  selectedId: string | null;
  locked: boolean;
  busy: boolean;
  warnings: string[];
  onSelect: (id: string) => void;
  onAdd: () => void;
  onDelete: (component: PlanComponent) => void;
}

function partLabel(component: PlanComponent): string {
  return component.component_name.replaceAll("_", " ");
}

export function ComponentPanel({
  furnitureType,
  components,
  selectedId,
  locked,
  busy,
  warnings,
  onSelect,
  onAdd,
  onDelete,
}: Props) {
  const addLabel = furnitureType === "bookshelf" ? "Add shelf" : "Add leg";
  return (
    <aside className="cad-components" aria-label="Furniture components">
      <div className="cad-panel-heading">
        <div><small>Model tree</small><strong>Components</strong></div>
        <span>{components.length}</span>
      </div>
      <div className="cad-component-list">
        {components.map((component, index) => (
          <div key={component.id} className={`cad-component-row${component.id === selectedId ? " is-selected" : ""}`}>
            <button type="button" onClick={() => onSelect(component.id)} title={`Select ${partLabel(component)}`}>
              <i className={`cad-part-icon cad-part-icon--${component.component_type}`} aria-hidden="true" />
              <span><strong>{partLabel(component)}</strong><small>{component.component_type} · #{String(index + 1).padStart(2, "0")}</small></span>
            </button>
            {!locked && component.id === selectedId && (
              <button
                type="button"
                className="cad-row-delete"
                title={`Delete ${partLabel(component)}`}
                aria-label={`Delete ${partLabel(component)}`}
                disabled={busy}
                onClick={() => onDelete(component)}
              >×</button>
            )}
          </div>
        ))}
      </div>
      <button type="button" className="cad-add-part" disabled={locked || busy} onClick={onAdd}>
        <span>＋</span>{addLabel}
      </button>
      {warnings.length > 0 && (
        <div className="cad-semantic-warning" role="status">
          <strong>Finish check</strong>
          {warnings.map((warning) => <p key={warning}>{warning}</p>)}
        </div>
      )}
      <div className="cad-panel-footnote">
        {locked ? "Components are inspectable but immutable." : "Delete removes a draft part only. Backend rules are checked when you finish."}
      </div>
    </aside>
  );
}
