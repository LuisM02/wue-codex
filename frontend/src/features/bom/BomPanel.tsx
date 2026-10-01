import { useEffect, useMemo, useState } from "react";

import { BusyLabel, Notice, SectionHeading } from "../../components/Feedback";
import { isDemoCatalogName, isWoodScrewMaterial } from "../../lib/catalog";
import { formatDate, formatNumber, unitLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type {
  BomHardwareCost,
  BomMaterialCost,
  BomSelection,
  Furniture,
  FurniturePlan,
  HardwareQuantity,
  Material,
  MaterialQuantity,
} from "../../types/api";

interface Props {
  furniture: Furniture;
  plan: FurniturePlan;
  initialSelection: BomSelection | null;
  onContinue: (selection: BomSelection) => void;
}

function partCount(quantity: MaterialQuantity | null): number {
  return quantity?.components.reduce((sum, item) => sum + item.quantity, 0) ?? 0;
}

export function BomPanel({ furniture, plan, initialSelection, onContinue }: Props) {
  const [woods, setWoods] = useState<Material[]>([]);
  const [hardware, setHardware] = useState<Material[]>([]);
  const [woodId, setWoodId] = useState(initialSelection?.material_id ?? "");
  const [hardwareId, setHardwareId] = useState(initialSelection?.hardware_material_id ?? "");
  const [materialQuantity, setMaterialQuantity] = useState<MaterialQuantity | null>(null);
  const [hardwareQuantity, setHardwareQuantity] = useState<HardwareQuantity | null>(null);
  const [materialCost, setMaterialCost] = useState<BomMaterialCost | null>(null);
  const [hardwareCost, setHardwareCost] = useState<BomHardwareCost | null>(null);
  const [busy, setBusy] = useState<"load" | "cost" | null>("load");
  const [setupBusy, setSetupBusy] = useState(false);
  const [woodName, setWoodName] = useState("Gmelina");
  const [woodPrice, setWoodPrice] = useState("");
  const [screwPrice, setScrewPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setBusy("load");
    setError(null);
    Promise.all([
      api.catalog.materials("wood"),
      api.catalog.materials("hardware"),
      api.plans.materialQuantity(plan.id),
      api.plans.hardwareQuantity(plan.id),
    ]).then(([woodItems, hardwareItems, materialResult, hardwareResult]) => {
      if (!current) return;
      const compatibleHardware = hardwareItems.filter(isWoodScrewMaterial);
      setWoods(woodItems);
      setHardware(compatibleHardware);
      setWoodId((value) => value || woodItems[0]?.id || "");
      setHardwareId((value) => value || compatibleHardware[0]?.id || "");
      setMaterialQuantity(materialResult);
      setHardwareQuantity(hardwareResult);
    }).catch((reason: Error) => {
      if (current) setError(reason.message);
    }).finally(() => {
      if (current) setBusy(null);
    });
    return () => { current = false; };
  }, [plan.id]);

  const selection = useMemo<BomSelection | null>(() => {
    if (!woodId || !hardwareId) return null;
    return { material_id: woodId, hardware_material_id: hardwareId };
  }, [woodId, hardwareId]);

  useEffect(() => {
    setMaterialCost(null);
    setHardwareCost(null);
    if (!selection) return;
    let current = true;
    setBusy("cost");
    setError(null);
    Promise.all([
      api.plans.materialCost(plan.id, selection.material_id),
      api.plans.hardwareCost(plan.id, selection.hardware_material_id),
    ]).then(([materialResult, hardwareResult]) => {
      if (!current) return;
      setMaterialCost(materialResult);
      setHardwareCost(hardwareResult);
    }).catch((reason: Error) => {
      if (current) setError(reason.message);
    }).finally(() => {
      if (current) setBusy(null);
    });
    return () => { current = false; };
  }, [plan.id, selection]);

  const catalogReady = woods.length > 0 && hardware.length > 0;
  const setupReady = (woods.length > 0 || Boolean(woodName.trim() && woodPrice.trim()))
    && (hardware.length > 0 || Boolean(screwPrice.trim()));
  const ready = Boolean(selection && materialCost && hardwareCost);
  const usesDemoPrices = isDemoCatalogName(woods.find((item) => item.id === woodId)?.material_name);
  const estimatedTotal = Number(materialCost?.total_cost ?? 0) + Number(hardwareCost?.total_cost ?? 0);

  async function createStarterCatalog() {
    const parsedWoodPrice = Number(woodPrice);
    const parsedScrewPrice = Number(screwPrice);
    if (!setupReady || (!woods.length && (!woodName.trim() || parsedWoodPrice < 0 || !Number.isFinite(parsedWoodPrice))) ||
        (!hardware.length && (parsedScrewPrice < 0 || !Number.isFinite(parsedScrewPrice)))) return;
    setSetupBusy(true);
    setError(null);
    try {
      let wood = woods[0];
      if (!wood) {
        wood = await api.catalog.createMaterial({
          material_name: woodName.trim(),
          material_type: "wood",
          unit: "board_ft",
          is_active: true,
        });
        await api.catalog.createMaterialPrice(wood.id, {
          price_per_unit: parsedWoodPrice,
          effective_date: new Date().toISOString().slice(0, 10),
        });
        setWoods([wood]);
      }
      let fastener = hardware[0];
      if (!fastener) {
        fastener = await api.catalog.createMaterial({
          material_name: "Wood screw",
          material_type: "hardware",
          unit: "piece",
          is_active: true,
        });
        await api.catalog.createMaterialPrice(fastener.id, {
          price_per_unit: parsedScrewPrice,
          effective_date: new Date().toISOString().slice(0, 10),
        });
        setHardware([fastener]);
      }
      setWoodId(wood.id);
      setHardwareId(fastener.id);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setSetupBusy(false);
    }
  }

  return (
    <section className="workspace-section workspace-section--wide bom-workspace">
      <SectionHeading eyebrow="Step 06 · Bill of materials" title="Review what the build requires">
        <span className="status-badge status-badge--finalized">Plan revision {plan.revision}</span>
      </SectionHeading>
      <p className="section-intro">
        WUE converts the finalized CAD parts into net material quantities. Select stock and hardware prices, then add labor in the quote.
      </p>

      {error && <Notice tone="danger">{error}</Notice>}
      {usesDemoPrices && <Notice tone="warning">Demonstration prices selected. These sample values illustrate the calculation and are not supplier prices.</Notice>}
      {!catalogReady && busy !== "load" && (
        <Notice tone="warning">
          Your local purchasing catalog is incomplete. Add the missing starter prices below; these values stay on this computer and can be expanded later.
        </Notice>
      )}

      {!catalogReady && busy !== "load" && (
        <div className="panel catalog-setup">
          <div className="panel__heading">
            <span className="panel__index">+</span>
            <div><h3>Set up local purchasing prices</h3><p>Enter your actual supplier prices. WUE will not invent market prices.</p></div>
          </div>
          <div className="catalog-setup__fields">
            {!woods.length && (
              <>
                <label className="field"><span>Wood name</span><input value={woodName} onChange={(event) => setWoodName(event.target.value)} /></label>
                <label className="field"><span>Price per board foot</span><input type="number" min="0" step="0.01" value={woodPrice} onChange={(event) => setWoodPrice(event.target.value)} placeholder="0.00" /></label>
              </>
            )}
            {!hardware.length && (
              <label className="field"><span>Wood screw price · each</span><input type="number" min="0" step="0.01" value={screwPrice} onChange={(event) => setScrewPrice(event.target.value)} placeholder="0.00" /></label>
            )}
            <button className="button button--primary" type="button" disabled={setupBusy || !setupReady} onClick={createStarterCatalog}>
              {setupBusy ? <BusyLabel>Saving catalog…</BusyLabel> : "Save starter catalog"}
            </button>
          </div>
        </div>
      )}

      <div className="quantity-ribbon">
        <article><span className="quantity-ribbon__icon">▧</span><div><small>CAD components</small><strong>{partCount(materialQuantity)} physical pieces</strong></div></article>
        <article><span className="quantity-ribbon__icon">◫</span><div><small>Solid volume</small><strong>{materialQuantity ? formatNumber(materialQuantity.total_volume_mm3, 0) : "—"} mm³</strong></div></article>
        <article><span className="quantity-ribbon__icon">⌁</span><div><small>Hardware</small><strong>{hardwareQuantity ? `${hardwareQuantity.total_quantity} pieces` : "—"}</strong></div></article>
      </div>

      <div className="panel bom-selection-panel">
        <div className="panel__heading">
          <span className="panel__index">1</span>
          <div><h3>Assign purchasing stock</h3><p>The latest dated catalog price is used for this working BOM.</p></div>
        </div>
        <div className="bom-selectors">
          <label className="field">
            <span>Wood material</span>
            <select value={woodId} onChange={(event) => setWoodId(event.target.value)}>
              <option value="">Choose wood…</option>
              {woods.map((item) => <option key={item.id} value={item.id}>{item.material_name} · per {unitLabel(item.unit)}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Fastener</span>
            <select value={hardwareId} onChange={(event) => setHardwareId(event.target.value)}>
              <option value="">Choose hardware…</option>
              {hardware.map((item) => <option key={item.id} value={item.id}>{item.material_name} · per piece</option>)}
            </select>
          </label>
          <div className="bom-running-total">
            <small>Materials subtotal</small>
            <strong>{ready ? formatNumber(estimatedTotal) : "—"}</strong>
            <span>Before labor</span>
          </div>
        </div>
      </div>

      <div className="bom-section">
        <header>
          <div><p className="eyebrow">Materials used</p><h3>Purchasing summary</h3></div>
          {busy === "cost" && <BusyLabel>Updating prices…</BusyLabel>}
        </header>
        <div className="bom-table-wrap">
          <table className="bom-table">
            <thead><tr><th>Name</th><th>Category</th><th>Parts</th><th>Required</th><th>Unit price</th><th>Est. cost</th></tr></thead>
            <tbody>
              <tr>
                <td><strong>{materialCost?.material_name ?? "Select wood material"}</strong></td>
                <td>Solid wood</td>
                <td>{partCount(materialQuantity)}</td>
                <td>{materialCost ? `${formatNumber(materialCost.total_quantity_in_price_unit)} ${unitLabel(materialCost.price_unit)}` : "—"}</td>
                <td>{materialCost ? formatNumber(materialCost.price_per_unit) : "—"}</td>
                <td><strong>{materialCost ? formatNumber(materialCost.total_cost) : "—"}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
        {materialCost && <p className="bom-price-note">Price effective {formatDate(materialCost.price_effective_date)} · calculated from exact CAD volume.</p>}
      </div>

      <div className="bom-section">
        <header><div><p className="eyebrow">Hardware used</p><h3>Connection schedule</h3></div></header>
        <div className="bom-table-wrap">
          <table className="bom-table">
            <thead><tr><th>Hardware</th><th>Connection rule</th><th>Connections</th><th>Quantity</th><th>Each</th><th>Est. cost</th></tr></thead>
            <tbody>
              <tr>
                <td><strong>{hardwareCost?.material_name ?? hardwareQuantity?.item_name ?? "Wood screw"}</strong></td>
                <td>{hardwareQuantity?.screws_per_connection ?? 2} per connection</td>
                <td>{hardwareQuantity?.total_connections ?? "—"}</td>
                <td>{hardwareQuantity ? `${hardwareQuantity.total_quantity} pieces` : "—"}</td>
                <td>{hardwareCost ? formatNumber(hardwareCost.price_per_piece) : "—"}</td>
                <td><strong>{hardwareCost ? formatNumber(hardwareCost.total_cost) : "—"}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
        {hardwareCost && <p className="bom-price-note">Price effective {formatDate(hardwareCost.price_effective_date)} · quantities follow the current connection rule.</p>}
        {plan.furniture_type === "dining_table" && plan.components.some((part) => part.component_name.endsWith("_apron")) && (
          <p className="bom-price-note">Prototype hardware rule: two screws per leg connection. Separate apron joints are not itemized yet.</p>
        )}
      </div>

      <div className="bom-section">
        <header><div><p className="eyebrow">Part breakdown</p><h3>CAD quantity audit</h3></div></header>
        <div className="bom-table-wrap">
          <table className="bom-table bom-table--parts">
            <thead><tr><th>Part</th><th>Type</th><th>Finished size</th><th>Qty</th><th>Total volume</th><th>Material cost</th></tr></thead>
            <tbody>
              {materialQuantity?.components.map((item) => {
                const priced = materialCost?.components.find((entry) => entry.source_component_id === item.source_component_id);
                return (
                  <tr key={item.source_component_id}>
                    <td><strong>{item.component_name}</strong></td>
                    <td>{item.component_type}</td>
                    <td>{formatNumber(item.width_mm)} × {formatNumber(item.height_mm)} × {formatNumber(item.depth_mm)} mm</td>
                    <td>{item.quantity}</td>
                    <td>{formatNumber(item.total_volume_mm3, 0)} mm³</td>
                    <td>{priced ? formatNumber(priced.cost) : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-footer">
        <div><small>Net modeled volume · cutting waste and stock layout require review</small><strong>{furniture.name} · finalized revision {plan.revision}</strong></div>
        <button className="button button--primary" disabled={!ready || !selection} onClick={() => selection && onContinue(selection)}>
          Continue to quote <span>→</span>
        </button>
      </div>
    </section>
  );
}
