import { Bounds, ContactShadows, Edges, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense, useEffect, useState } from "react";
import { Color } from "three";

import { BusyLabel, Notice, SectionHeading } from "../../components/Feedback";
import { formatNumber, furnitureLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type { Furniture, FurniturePlan, GeometryComponent, PlanGeometry } from "../../types/api";

const finishes = [
  { name: "Natural oak", color: "#b9824f" },
  { name: "Warm walnut", color: "#70452f" },
  { name: "Smoked ash", color: "#514941" },
  { name: "Blackened", color: "#292a27" },
  { name: "Chalk", color: "#d8d1c2" },
  { name: "Forest", color: "#425a49" },
];

function Part({
  part,
  color,
  selected,
  onSelect,
}: {
  part: GeometryComponent;
  color: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const dimensions = [Number(part.dimensions.width), Number(part.dimensions.height), Number(part.dimensions.depth)] as [number, number, number];
  const center = [Number(part.center.x), Number(part.center.y), Number(part.center.z)] as [number, number, number];
  const surface = new Color(color);
  if (part.component_type === "leg") surface.multiplyScalar(0.82);
  return (
    <mesh
      position={center}
      rotation={[0, Number(part.rotation_degrees) * Math.PI / 180, 0]}
      onClick={(event) => { event.stopPropagation(); onSelect(); }}
      castShadow
      receiveShadow
    >
      <boxGeometry args={dimensions} />
      <meshStandardMaterial color={surface} roughness={0.72} metalness={0.02} />
      <Edges color={selected ? "#f4d08a" : "#432d20"} threshold={15} lineWidth={selected ? 2 : 0.65} />
    </mesh>
  );
}

function Model({
  geometry,
  color,
  selectedId,
  onSelect,
}: {
  geometry: PlanGeometry;
  color: string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}) {
  return (
    <Bounds fit clip observe margin={1.3}>
      <group onPointerMissed={() => onSelect(null)}>
        {geometry.components.map((part) => (
          <Part
            key={part.source_component_id}
            part={part}
            color={color}
            selected={selectedId === part.source_component_id}
            onSelect={() => onSelect(part.source_component_id)}
          />
        ))}
      </group>
    </Bounds>
  );
}

interface Props {
  furniture: Furniture;
  plan: FurniturePlan;
  onContinue: () => void;
}

export function FurnitureViewer({ furniture, plan, onContinue }: Props) {
  const [geometry, setGeometry] = useState<PlanGeometry | null>(null);
  const [finish, setFinish] = useState(finishes[1]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setGeometry(null);
    setError(null);
    api.plans.geometry(plan.id)
      .then((value) => { if (current) setGeometry(value); })
      .catch((reason: Error) => { if (current) setError(reason.message); });
    return () => { current = false; };
  }, [plan.id]);

  const selected = geometry?.components.find((part) => part.source_component_id === selectedId) ?? null;

  return (
    <section className="workspace-section workspace-section--wide">
      <SectionHeading eyebrow="Step 05 · Deterministic reconstruction" title="Inspect the piece in three dimensions">
        <span className="status-badge status-badge--finalized">Revision {plan.revision} · locked</span>
      </SectionHeading>
      <p className="section-intro">
        Drag to orbit, scroll to zoom, and select a part for its exact dimensions. Every box comes directly from the finalized plan.
      </p>
      {error && <Notice tone="danger">{error}</Notice>}

      <div className="viewer-layout">
        <div className="viewer-stage">
          {!geometry ? (
            <div className="viewer-loading"><BusyLabel>Building model…</BusyLabel></div>
          ) : (
            <Canvas shadows camera={{ position: [1000, 800, 1200], fov: 42 }} dpr={[1, 2]}>
              <color attach="background" args={["#e9e5dc"]} />
              <fog attach="fog" args={["#e9e5dc", 2500, 9000]} />
              <ambientLight intensity={1.5} />
              <directionalLight position={[1400, 2200, 1600]} intensity={2.2} castShadow shadow-mapSize={[1024, 1024]} />
              <directionalLight position={[-1200, 900, -800]} intensity={0.8} />
              <Suspense fallback={null}>
                <Model geometry={geometry} color={finish.color} selectedId={selectedId} onSelect={setSelectedId} />
                <ContactShadows position={[0, -3, 0]} opacity={0.32} scale={5000} blur={2.5} far={3000} />
              </Suspense>
              <OrbitControls makeDefault enableDamping dampingFactor={0.08} />
            </Canvas>
          )}
          <div className="viewer-stage__hint"><span>↻</span> Drag to rotate <span>＋</span> Scroll to zoom</div>
          {selected && (
            <div className="part-inspector">
              <button type="button" aria-label="Close part details" onClick={() => setSelectedId(null)}>×</button>
              <small>Selected part</small>
              <strong>{selected.component_name}</strong>
              <span>{formatNumber(selected.dimensions.width)} × {formatNumber(selected.dimensions.height)} × {formatNumber(selected.dimensions.depth)} mm · qty {selected.quantity}</span>
            </div>
          )}
        </div>

        <aside className="viewer-sidebar">
          <div className="panel appearance-panel">
            <p className="eyebrow">Visual appearance</p>
            <h3>Choose a preview finish</h3>
            <p>This changes only the model’s color. Your costing material is selected separately in the next step.</p>
            <div className="finish-swatches">
              {finishes.map((item) => (
                <button
                  key={item.name}
                  type="button"
                  className={finish.name === item.name ? "is-selected" : ""}
                  onClick={() => setFinish(item)}
                  title={item.name}
                >
                  <i style={{ background: item.color }} />
                  <span>{item.name}</span>
                </button>
              ))}
            </div>
          </div>
          <div className="panel model-facts">
            <small>Model facts</small>
            <strong>{furniture.name}</strong>
            <dl>
              <div><dt>Type</dt><dd>{furniture.furniture_type ? furnitureLabel(furniture.furniture_type) : furnitureLabel(plan.furniture_type)}</dd></div>
              <div><dt>Definitions</dt><dd>{geometry?.components.length ?? "—"}</dd></div>
              <div><dt>Total pieces</dt><dd>{geometry?.components.reduce((sum, part) => sum + part.quantity, 0) ?? "—"}</dd></div>
              <div><dt>Unit</dt><dd>Millimeter</dd></div>
            </dl>
          </div>
        </aside>
      </div>

      <div className="section-footer">
        <div><small>Appearance</small><strong>{finish.name} preview · not linked to pricing</strong></div>
        <button className="button button--primary" disabled={!geometry} onClick={onContinue}>Build estimate <span>→</span></button>
      </div>
    </section>
  );
}
