import { useEffect, useState, type FormEvent } from "react";

import { BusyLabel, EmptyState, Notice, SectionHeading } from "../../components/Feedback";
import { furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { Furniture, Project } from "../../types/api";

interface Props {
  projects: Project[];
  project: Project | null;
  furniture: Furniture | null;
  onProject: (project: Project | null) => void;
  onFurniture: (furniture: Furniture | null) => void;
  onProjectsChanged: (projects: Project[]) => void;
  onContinue: () => void;
}

export function ProjectSetup({
  projects,
  project,
  furniture,
  onProject,
  onFurniture,
  onProjectsChanged,
  onContinue,
}: Props) {
  const [pieces, setPieces] = useState<Furniture[]>([]);
  const [projectName, setProjectName] = useState("");
  const [description, setDescription] = useState("");
  const [pieceName, setPieceName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!project) {
      setPieces([]);
      return;
    }
    let current = true;
    api.furniture.list(project.id)
      .then((items) => { if (current) setPieces(items); })
      .catch((reason: Error) => { if (current) setError(reason.message); });
    return () => { current = false; };
  }, [project]);

  async function createProject(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const created = await api.projects.create({
        name: projectName,
        description: description.trim() || null,
      });
      onProjectsChanged([created, ...projects]);
      onProject(created);
      onFurniture(null);
      setProjectName("");
      setDescription("");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function createPiece(event: FormEvent) {
    event.preventDefault();
    if (!project) return;
    setBusy(true);
    setError(null);
    try {
      const created = await api.furniture.create(project.id, { name: pieceName });
      setPieces((items) => [created, ...items]);
      onFurniture(created);
      setPieceName("");
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function selectProject(id: string) {
    const selected = projects.find((item) => item.id === id) ?? null;
    onProject(selected);
    onFurniture(null);
  }

  return (
    <section className="workspace-section">
      <SectionHeading eyebrow="Step 01 · The work" title="Start with the furniture in front of you" />
      <p className="section-intro">
        Name the job and the furniture piece. You do not need to decide whether it is a chair, dining table, or bookshelf—the photo analysis does that next.
      </p>
      {error && <Notice tone="danger">{error}</Notice>}

      <div className="setup-grid">
        <div className="panel panel--soft">
          <div className="panel__heading">
            <span className="panel__index">A</span>
            <div><h3>Project</h3><p>Select an existing job or begin a new one.</p></div>
          </div>
          <label className="field">
            <span>Existing projects</span>
            <select value={project?.id ?? ""} onChange={(event) => selectProject(event.target.value)}>
              <option value="">Choose a project…</option>
              {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
            </select>
          </label>
          <div className="divider"><span>or create one</span></div>
          <form onSubmit={createProject} className="form-stack">
            <label className="field"><span>Project name</span><input required maxLength={200} value={projectName} onChange={(e) => setProjectName(e.target.value)} placeholder="Dining room restoration" /></label>
            <label className="field"><span>Notes <em>optional</em></span><textarea maxLength={2000} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="Client brief, location, or useful context" /></label>
            <button className="button button--secondary" disabled={busy || !projectName.trim()}>{busy ? <BusyLabel /> : "Create project"}</button>
          </form>
        </div>

        <div className={`panel${!project ? " panel--disabled" : ""}`}>
          <div className="panel__heading">
            <span className="panel__index">B</span>
            <div><h3>Furniture piece</h3><p>WUE supports chairs, dining tables, and bookshelves.</p></div>
          </div>
          {!project ? (
            <EmptyState title="Choose a project first">The furniture list will appear here.</EmptyState>
          ) : (
            <>
              <label className="field">
                <span>Existing pieces</span>
                <select value={furniture?.id ?? ""} onChange={(e) => onFurniture(pieces.find((item) => item.id === e.target.value) ?? null)}>
                  <option value="">Choose a piece…</option>
                  {pieces.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.furniture_type ? furnitureLabel(item.furniture_type) : "Awaiting AI"}</option>)}
                </select>
              </label>
              <div className="divider"><span>or add one</span></div>
              <form onSubmit={createPiece} className="form-stack">
                <label className="field"><span>Piece name</span><input required maxLength={200} value={pieceName} onChange={(e) => setPieceName(e.target.value)} placeholder="Walnut dining chair" /></label>
                <div className="ai-type-note">
                  <span aria-hidden="true">◎</span>
                  <div><strong>No type needed</strong><p>WUE will identify chair, dining table, or bookshelf after the photographs are analyzed.</p></div>
                </div>
                <button className="button button--secondary" disabled={busy || !pieceName.trim()}>{busy ? <BusyLabel /> : "Add furniture piece"}</button>
              </form>
            </>
          )}
        </div>
      </div>

      {project && furniture && (
        <div className="selection-summary">
          {furniture.furniture_type ? <span className={`furniture-glyph furniture-glyph--${furniture.furniture_type}`} aria-hidden="true" /> : <span className="pending-glyph" aria-hidden="true">?</span>}
          <div><small>Ready to begin</small><strong>{project.name} / {furniture.name}</strong></div>
          <button className="button button--primary" onClick={onContinue}>Add five photos <span>→</span></button>
        </div>
      )}
    </section>
  );
}
