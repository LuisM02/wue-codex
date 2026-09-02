import type { OrthographicView } from "./editorGeometry";

interface Props {
  view: OrthographicView;
  gridVisible: boolean;
  snapEnabled: boolean;
  photoVisible: boolean;
  hasPhoto: boolean;
  locked: boolean;
  busy: boolean;
  canUndo: boolean;
  canRedo: boolean;
  zoom: number;
  onView: (view: OrthographicView) => void;
  onGrid: () => void;
  onSnap: () => void;
  onPhoto: () => void;
  onUndo: () => void;
  onRedo: () => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
  onFinish: () => void;
}

function ToolButton({
  label,
  icon,
  title,
  active = false,
  disabled = false,
  onClick,
}: {
  label: string;
  icon: string;
  title: string;
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`cad-tool${active ? " is-active" : ""}`}
      title={title}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
    >
      <span aria-hidden="true">{icon}</span>
      <small>{label}</small>
    </button>
  );
}

export function EditorToolbar(props: Props) {
  return (
    <header className="cad-toolbar" aria-label="2D editor tools">
      <div className="cad-toolbar__group">
        <ToolButton label="Select" icon="⌖" title="Select and move components" active onClick={() => undefined} />
      </div>
      <div className="cad-toolbar__group" aria-label="Orthographic view">
        {(["front", "side", "top"] as const).map((view) => (
          <ToolButton
            key={view}
            label={view[0].toUpperCase() + view.slice(1)}
            icon={view === "front" ? "▣" : view === "side" ? "▥" : "▤"}
            title={`Show ${view} orthographic view`}
            active={props.view === view}
            onClick={() => props.onView(view)}
          />
        ))}
      </div>
      <div className="cad-toolbar__group">
        <ToolButton label="Grid" icon="#" title="Toggle drawing grid" active={props.gridVisible} onClick={props.onGrid} />
        <ToolButton label="Snap" icon="⊹" title="Snap movement and resizing to the grid and nearby edges" active={props.snapEnabled} onClick={props.onSnap} />
        {props.hasPhoto && (
          <ToolButton label="Photo" icon="◩" title="Toggle the front reference photograph" active={props.photoVisible} disabled={props.view !== "front"} onClick={props.onPhoto} />
        )}
      </div>
      <div className="cad-toolbar__group">
        <ToolButton label="Undo" icon="↶" title="Undo last saved edit (Ctrl+Z)" disabled={props.locked || props.busy || !props.canUndo} onClick={props.onUndo} />
        <ToolButton label="Redo" icon="↷" title="Redo last saved edit (Ctrl+Y)" disabled={props.locked || props.busy || !props.canRedo} onClick={props.onRedo} />
      </div>
      <div className="cad-toolbar__group">
        <ToolButton label="Zoom in" icon="＋" title="Zoom in (+)" onClick={props.onZoomIn} />
        <ToolButton label="Zoom out" icon="−" title="Zoom out (-)" onClick={props.onZoomOut} />
        <ToolButton label="Fit" icon="⛶" title="Fit all components to view" onClick={props.onFit} />
        <span className="cad-zoom-readout">{Math.round(props.zoom * 100)}%</span>
      </div>
      <button
        type="button"
        className="cad-finish"
        disabled={props.locked || props.busy}
        onClick={props.onFinish}
        title={props.locked ? "This revision is finalized and locked" : "Validate and finalize this 2D revision"}
      >
        {props.locked ? "Finalized / locked" : props.busy ? "Saving…" : "Finish 2D"}
      </button>
    </header>
  );
}
