import { useRef, useState, type ChangeEvent } from "react";

import { BusyLabel, Notice, SectionHeading } from "../../components/Feedback";
import { formatFileSize, furnitureLabel } from "../../lib/format";
import { ApiError, api } from "../../services/apiClient";
import type {
  Furniture,
  FurnitureClassification,
  FurnitureImage,
  ImageView,
} from "../../types/api";

const views: Array<{ id: ImageView; label: string; guide: string }> = [
  { id: "front", label: "Front", guide: "Square to the front face" },
  { id: "back", label: "Back", guide: "Show the rear construction" },
  { id: "left", label: "Left", guide: "Keep the full silhouette" },
  { id: "right", label: "Right", guide: "Match the left-side height" },
  { id: "top", label: "Top", guide: "Photograph from directly above" },
];

interface Props {
  furniture: Furniture;
  images: FurnitureImage[];
  classification: FurnitureClassification | null;
  onImages: (images: FurnitureImage[]) => void;
  onClassification: (value: FurnitureClassification | null) => void;
  onContinue: () => void;
}

export function ImageWorkspace({
  furniture,
  images,
  classification,
  onImages,
  onClassification,
  onContinue,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [pendingView, setPendingView] = useState<ImageView | null>(null);
  const [busyView, setBusyView] = useState<ImageView | null>(null);
  const [classifying, setClassifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const complete = images.length === views.length;

  function openPicker(view: ImageView) {
    setPendingView(view);
    inputRef.current?.click();
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !pendingView) return;
    setBusyView(pendingView);
    setError(null);
    try {
      const created = await api.images.upload(furniture.id, pendingView, file);
      onImages([...images.filter((item) => item.view !== created.view), created]);
      onClassification(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusyView(null);
      setPendingView(null);
    }
  }

  async function remove(view: ImageView) {
    setBusyView(view);
    setError(null);
    try {
      await api.images.remove(furniture.id, view);
      onImages(images.filter((item) => item.view !== view));
      onClassification(null);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusyView(null);
    }
  }

  async function classify() {
    setClassifying(true);
    setError(null);
    try {
      onClassification(await api.classification.run(furniture.id));
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 503) {
        setError("Automated recognition is not connected yet. Your selected furniture type is kept, so you can continue measuring the piece.");
      } else {
        setError((reason as Error).message);
      }
    } finally {
      setClassifying(false);
    }
  }

  return (
    <section className="workspace-section">
      <SectionHeading eyebrow="Step 02 · Visual reference" title="Photograph all five sides">
        <span className={`progress-pill${complete ? " is-complete" : ""}`}>
          {complete ? "✓ Complete" : `${images.length} of 5 added`}
        </span>
      </SectionHeading>
      <p className="section-intro">
        Even lighting and straight-on angles make the reconstruction easier to verify. JPEG, PNG, and WebP images are accepted.
      </p>
      {error && <Notice tone="warning">{error}</Notice>}
      <input ref={inputRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={upload} />

      <div className="photo-grid">
        {views.map((view) => {
          const image = images.find((item) => item.view === view.id);
          const busy = busyView === view.id;
          return (
            <article key={view.id} className={`photo-card${image ? " has-image" : ""}`}>
              <div className="photo-card__preview">
                {image ? (
                  <img src={api.images.contentUrl(furniture.id, view.id)} alt={`${view.label} view of ${furniture.name}`} />
                ) : (
                  <button type="button" onClick={() => openPicker(view.id)} disabled={busy}>
                    <span className="photo-card__cross" aria-hidden="true">+</span>
                    <strong>{busy ? <BusyLabel>Uploading…</BusyLabel> : "Add photo"}</strong>
                  </button>
                )}
                <span className="photo-card__view">{view.label}</span>
              </div>
              <div className="photo-card__details">
                <div>
                  <strong>{view.label} view</strong>
                  <small>{image ? `${image.pixel_width} × ${image.pixel_height} · ${formatFileSize(image.file_size_bytes)}` : view.guide}</small>
                </div>
                {image && (
                  <div className="photo-card__actions">
                    <button type="button" className="text-button" disabled={busy} onClick={() => remove(view.id)}>{busy ? "Removing…" : "Remove"}</button>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>

      <div className={`classification-strip${complete ? " is-ready" : ""}`}>
        <div className="classification-strip__icon" aria-hidden="true">◎</div>
        <div>
          <small>Furniture recognition</small>
          {classification ? (
            <strong>{furnitureLabel(classification.predicted_type)}{classification.confidence ? ` · ${Math.round(Number(classification.confidence) * 100)}% confidence` : ""}</strong>
          ) : (
            <strong>{complete ? "Five views are ready to check" : "Available after all five photos"}</strong>
          )}
        </div>
        <button className="button button--secondary" disabled={!complete || classifying} onClick={classify}>
          {classifying ? <BusyLabel>Checking…</BusyLabel> : classification ? "Check again" : "Recognize piece"}
        </button>
      </div>

      <div className="section-footer">
        <div>
          <small>Selected piece</small>
          <strong>{furniture.name} · {furnitureLabel(furniture.furniture_type)}</strong>
        </div>
        <button className="button button--primary" disabled={!complete} onClick={onContinue}>Set dimensions <span>→</span></button>
      </div>
    </section>
  );
}
