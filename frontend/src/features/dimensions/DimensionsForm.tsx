import { useEffect, useMemo, useState, type FormEvent } from "react";

import { BusyLabel, Notice, SectionHeading } from "../../components/Feedback";
import { formatNumber, furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { DimensionUnit, Furniture, FurnitureDimensions } from "../../types/api";

const units: Array<{ value: DimensionUnit; label: string }> = [
  { value: "mm", label: "Millimeters" },
  { value: "cm", label: "Centimeters" },
  { value: "m", label: "Meters" },
  { value: "in", label: "Inches" },
];

const mmPerUnit: Record<DimensionUnit, number> = { mm: 1, cm: 10, m: 1000, in: 25.4 };

function fromMillimeters(value: string, unit: DimensionUnit): string {
  return String(Number(value) / mmPerUnit[unit]);
}

interface Props {
  furniture: Furniture;
  dimensions: FurnitureDimensions | null;
  onDimensions: (dimensions: FurnitureDimensions) => void;
  onContinue: () => void;
}

export function DimensionsForm({ furniture, dimensions, onDimensions, onContinue }: Props) {
  const [unit, setUnit] = useState<DimensionUnit>(dimensions?.unit ?? "mm");
  const [width, setWidth] = useState("");
  const [height, setHeight] = useState("");
  const [depth, setDepth] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!dimensions) return;
    const savedUnit = dimensions.unit;
    setUnit(savedUnit);
    setWidth(fromMillimeters(dimensions.width_mm, savedUnit));
    setHeight(fromMillimeters(dimensions.height_mm, savedUnit));
    setDepth(fromMillimeters(dimensions.depth_mm, savedUnit));
  }, [dimensions]);

  const valid = useMemo(
    () => [width, height, depth].every((value) => Number(value) > 0 && Number.isFinite(Number(value))),
    [width, height, depth],
  );

  function changeUnit(nextUnit: DimensionUnit) {
    if (valid) {
      const conversion = mmPerUnit[unit] / mmPerUnit[nextUnit];
      setWidth(String(Number(width) * conversion));
      setHeight(String(Number(height) * conversion));
      setDepth(String(Number(depth) * conversion));
    }
    setUnit(nextUnit);
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const saved = await api.dimensions.save(furniture.id, {
        width: Number(width),
        height: Number(height),
        depth: Number(depth),
        unit,
        source: "manual",
      });
      onDimensions(saved);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="workspace-section">
      <SectionHeading eyebrow="Step 03 · Overall scale" title="Measure the outside dimensions">
        {dimensions && <span className="progress-pill is-complete">✓ Saved</span>}
      </SectionHeading>
      <p className="section-intro">
        Measure the widest, tallest, and deepest points. WUE stores a precise millimeter reference no matter which unit you use here.
      </p>
      {error && <Notice tone="danger">{error}</Notice>}

      <div className="measurement-layout">
        <div className="measurement-visual" aria-hidden="true">
          <div className={`dimension-sketch dimension-sketch--${furniture.furniture_type}`}>
            <span className="dimension-line dimension-line--width"><i /><b>{width || "W"} {unit}</b></span>
            <span className="dimension-line dimension-line--height"><i /><b>{height || "H"} {unit}</b></span>
            <span className="dimension-line dimension-line--depth"><i /><b>{depth || "D"} {unit}</b></span>
            <div className="dimension-sketch__object">
              <span className={`furniture-glyph furniture-glyph--${furniture.furniture_type}`} />
            </div>
          </div>
          <div className="measurement-visual__caption">
            <small>Measuring</small>
            <strong>{furniture.name}</strong>
            <span>{furnitureLabel(furniture.furniture_type)}</span>
          </div>
        </div>

        <form className="panel measurement-form" onSubmit={save}>
          <div className="panel__heading">
            <span className="panel__index">↔</span>
            <div><h3>Overall measurements</h3><p>Enter positive values for every direction.</p></div>
          </div>
          <label className="field">
            <span>Measurement unit</span>
            <select value={unit} onChange={(e) => changeUnit(e.target.value as DimensionUnit)}>
              {units.map((item) => <option key={item.value} value={item.value}>{item.label} ({item.value})</option>)}
            </select>
          </label>
          <div className="dimension-fields">
            <label className="field"><span>Width</span><div className="input-unit"><input required type="number" min="0.000001" step="any" value={width} onChange={(e) => setWidth(e.target.value)} placeholder="450" /><b>{unit}</b></div></label>
            <label className="field"><span>Height</span><div className="input-unit"><input required type="number" min="0.000001" step="any" value={height} onChange={(e) => setHeight(e.target.value)} placeholder="900" /><b>{unit}</b></div></label>
            <label className="field"><span>Depth</span><div className="input-unit"><input required type="number" min="0.000001" step="any" value={depth} onChange={(e) => setDepth(e.target.value)} placeholder="500" /><b>{unit}</b></div></label>
          </div>
          {dimensions && (
            <Notice tone="neutral">
              Stored reference: {formatNumber(dimensions.width_mm)} × {formatNumber(dimensions.height_mm)} × {formatNumber(dimensions.depth_mm)} mm
            </Notice>
          )}
          <button className="button button--secondary button--wide" disabled={!valid || busy}>
            {busy ? <BusyLabel>Saving…</BusyLabel> : dimensions ? "Update dimensions" : "Save dimensions"}
          </button>
        </form>
      </div>

      <div className="section-footer">
        <div><small>Why this matters</small><strong>These measurements drive every generated part.</strong></div>
        <button className="button button--primary" disabled={!dimensions} onClick={onContinue}>Generate 2D plan <span>→</span></button>
      </div>
    </section>
  );
}
