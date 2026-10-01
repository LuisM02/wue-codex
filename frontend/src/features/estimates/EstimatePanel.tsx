import { useEffect, useMemo, useState } from "react";

import { BusyLabel, Notice, SectionHeading } from "../../components/Feedback";
import { isDemoCatalogName, isWoodScrewMaterial } from "../../lib/catalog";
import { formatDate, formatNumber, unitLabel } from "../../lib/format";
import { api } from "../../services/apiClient";
import type {
  BomSelection,
  CompleteCost,
  CostSelection,
  Furniture,
  FurniturePlan,
  HardwareQuantity,
  LaborQuantity,
  LaborRate,
  Material,
  MaterialQuantity,
  Quotation,
} from "../../types/api";

interface Props {
  furniture: Furniture;
  plan: FurniturePlan;
  initialSelection: BomSelection | null;
}

export function EstimatePanel({ furniture, plan, initialSelection }: Props) {
  const [woods, setWoods] = useState<Material[]>([]);
  const [hardware, setHardware] = useState<Material[]>([]);
  const [laborRates, setLaborRates] = useState<LaborRate[]>([]);
  const [woodId, setWoodId] = useState(initialSelection?.material_id ?? "");
  const [hardwareId, setHardwareId] = useState(initialSelection?.hardware_material_id ?? "");
  const [laborRateId, setLaborRateId] = useState("");
  const [materialQuantity, setMaterialQuantity] = useState<MaterialQuantity | null>(null);
  const [hardwareQuantity, setHardwareQuantity] = useState<HardwareQuantity | null>(null);
  const [laborQuantity, setLaborQuantity] = useState<LaborQuantity | null>(null);
  const [estimate, setEstimate] = useState<CompleteCost | null>(null);
  const [quotations, setQuotations] = useState<Quotation[]>([]);
  const [busy, setBusy] = useState<string | null>("load");
  const [laborSetupBusy, setLaborSetupBusy] = useState(false);
  const [laborName, setLaborName] = useState("Standard workshop rate");
  const [laborPrice, setLaborPrice] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let current = true;
    setBusy("load");
    setError(null);
    Promise.all([
      api.catalog.materials("wood"),
      api.catalog.materials("hardware"),
      api.catalog.laborRates(),
      api.plans.materialQuantity(plan.id),
      api.plans.hardwareQuantity(plan.id),
      api.plans.laborQuantity(plan.id),
      api.estimates.listQuotations(plan.id),
    ]).then(([woodItems, hardwareItems, rates, materialQty, hardwareQty, laborQty, quotes]) => {
      if (!current) return;
      const compatibleHardware = hardwareItems.filter(isWoodScrewMaterial);
      setWoods(woodItems);
      setHardware(compatibleHardware);
      setLaborRates(rates);
      setWoodId((value) => value || woodItems[0]?.id || "");
      setHardwareId((value) => value || compatibleHardware[0]?.id || "");
      setLaborRateId((value) => value || rates[0]?.id || "");
      setMaterialQuantity(materialQty);
      setHardwareQuantity(hardwareQty);
      setLaborQuantity(laborQty);
      setQuotations(quotes);
    }).catch((reason: Error) => {
      if (current) setError(reason.message);
    }).finally(() => {
      if (current) setBusy(null);
    });
    return () => { current = false; };
  }, [plan.id]);

  const selection = useMemo<CostSelection | null>(() => {
    if (!woodId || !hardwareId || !laborRateId) return null;
    return { material_id: woodId, hardware_material_id: hardwareId, labor_rate_id: laborRateId };
  }, [woodId, hardwareId, laborRateId]);

  async function calculate() {
    if (!selection) return;
    setBusy("calculate");
    setError(null);
    try {
      setEstimate(await api.estimates.complete(plan.id, selection));
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function createQuotation() {
    if (!selection || !estimate) return;
    setBusy("quote");
    setError(null);
    try {
      const created = await api.estimates.createQuotation(plan.id, selection);
      setQuotations((items) => [created, ...items]);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setBusy(null);
    }
  }

  async function createStarterLaborRate() {
    const parsedPrice = Number(laborPrice);
    if (!laborName.trim() || !laborPrice.trim() || parsedPrice < 0 || !Number.isFinite(parsedPrice)) return;
    setLaborSetupBusy(true);
    setError(null);
    try {
      const rate = await api.catalog.createLaborRate({ rate_name: laborName.trim(), is_active: true });
      await api.catalog.createLaborRatePrice(rate.id, {
        rate_per_hour: parsedPrice,
        effective_date: new Date().toISOString().slice(0, 10),
      });
      setLaborRates([rate]);
      setLaborRateId(rate.id);
    } catch (reason) {
      setError((reason as Error).message);
    } finally {
      setLaborSetupBusy(false);
    }
  }

  const catalogReady = woods.length > 0 && hardware.length > 0 && laborRates.length > 0;
  const usesDemoPrices = isDemoCatalogName(woods.find((item) => item.id === woodId)?.material_name)
    || isDemoCatalogName(laborRates.find((item) => item.id === laborRateId)?.rate_name);

  return (
    <section className="workspace-section workspace-section--wide estimate-workspace">
      <SectionHeading eyebrow="Step 07 · Transparent costing" title="Build the final estimate">
        <span className="status-badge status-badge--finalized">Plan revision {plan.revision}</span>
      </SectionHeading>
      <p className="section-intro">
        Select costing resources independently of the 3D finish. WUE uses each item’s latest dated price and preserves it when you create a quotation.
      </p>
      {error && <Notice tone="danger">{error}</Notice>}
      {usesDemoPrices && <Notice tone="warning">Demonstration estimate using sample catalog prices. Replace them with supplier and workshop prices before quoting real work.</Notice>}
      {!catalogReady && busy !== "load" && (
        <Notice tone="warning">
          The pricing catalog needs at least one active wood material, an active hardware item named “Wood screw,” and one labor rate—with dated prices—before a complete estimate can be calculated.
        </Notice>
      )}
      {!laborRates.length && busy !== "load" && (
        <div className="panel catalog-setup">
          <div className="panel__heading">
            <span className="panel__index">+</span>
            <div><h3>Set up a labor rate</h3><p>Use your workshop’s actual hourly rate. It remains editable through the local catalog.</p></div>
          </div>
          <div className="catalog-setup__fields catalog-setup__fields--labor">
            <label className="field"><span>Rate name</span><input value={laborName} onChange={(event) => setLaborName(event.target.value)} /></label>
            <label className="field"><span>Price per hour</span><input type="number" min="0" step="0.01" value={laborPrice} onChange={(event) => setLaborPrice(event.target.value)} placeholder="0.00" /></label>
            <button className="button button--primary" type="button" disabled={laborSetupBusy || !laborName.trim() || !laborPrice.trim()} onClick={createStarterLaborRate}>
              {laborSetupBusy ? <BusyLabel>Saving rate…</BusyLabel> : "Save labor rate"}
            </button>
          </div>
        </div>
      )}

      <div className="quantity-ribbon">
        <article><span className="quantity-ribbon__icon">▧</span><div><small>Solid material</small><strong>{materialQuantity ? formatNumber(materialQuantity.total_volume_mm3, 0) : "—"} mm³</strong></div></article>
        <article><span className="quantity-ribbon__icon">⌁</span><div><small>Wood screws</small><strong>{hardwareQuantity ? `${hardwareQuantity.total_quantity} pieces` : "—"}</strong></div></article>
        <article><span className="quantity-ribbon__icon">◷</span><div><small>Workshop labor</small><strong>{laborQuantity ? `${formatNumber(laborQuantity.labor_hours)} hours` : "—"}</strong></div></article>
      </div>

      <div className="estimate-layout">
        <div className="panel estimate-builder">
          <div className="panel__heading">
            <span className="panel__index">1</span>
            <div><h3>Choose costing resources</h3><p>Only active catalog entries are shown.</p></div>
          </div>
          <label className="field">
            <span>Wood material</span>
            <select value={woodId} onChange={(e) => { setWoodId(e.target.value); setEstimate(null); }}>
              <option value="">Choose wood…</option>
              {woods.map((item) => <option key={item.id} value={item.id}>{item.material_name} · per {unitLabel(item.unit)}</option>)}
            </select>
          </label>
          <label className="field">
            <span>Hardware</span>
            <select value={hardwareId} onChange={(e) => { setHardwareId(e.target.value); setEstimate(null); }}>
              <option value="">Choose hardware…</option>
              {hardware.map((item) => <option key={item.id} value={item.id}>{item.material_name} · per piece</option>)}
            </select>
          </label>
          <label className="field">
            <span>Labor rate</span>
            <select value={laborRateId} onChange={(e) => { setLaborRateId(e.target.value); setEstimate(null); }}>
              <option value="">Choose labor rate…</option>
              {laborRates.map((item) => <option key={item.id} value={item.id}>{item.rate_name}</option>)}
            </select>
          </label>
          <button className="button button--primary button--wide" onClick={calculate} disabled={!selection || Boolean(busy)}>
            {busy === "calculate" || busy === "load" ? <BusyLabel>Calculating…</BusyLabel> : "Calculate complete cost"}
          </button>
          <p className="form-footnote">No overhead, markup, tax, or currency is added. The total is the exact sum of material, hardware, and labor.</p>
          {plan.furniture_type === "dining_table" && plan.components.some((part) => part.component_name.endsWith("_apron")) && (
            <p className="form-footnote">Prototype labor covers base assembly, legs, and tabletop. Separate apron work and apron fasteners are not itemized in the current rules.</p>
          )}
        </div>

        <div className={`estimate-result${estimate ? " has-result" : ""}`}>
          {!estimate ? (
            <div className="estimate-result__empty">
              <span>∑</span>
              <h3>Your calculation will appear here</h3>
              <p>Choose three priced resources, then calculate the complete cost.</p>
            </div>
          ) : (
            <>
              <header><div><small>Complete cost</small><strong>{formatNumber(estimate.total_cost)}</strong></div><span>Exact total</span></header>
              <div className="cost-lines">
                <article>
                  <div><span className="cost-dot cost-dot--wood" /><div><strong>{estimate.material.material_name}</strong><small>{formatNumber(estimate.material.total_quantity_in_price_unit)} {unitLabel(estimate.material.price_unit)} × {formatNumber(estimate.material.price_per_unit)}</small></div></div>
                  <b>{formatNumber(estimate.material.total_cost)}</b>
                </article>
                <article>
                  <div><span className="cost-dot cost-dot--hardware" /><div><strong>{estimate.hardware.material_name}</strong><small>{estimate.hardware.quantity} pieces × {formatNumber(estimate.hardware.price_per_piece)}</small></div></div>
                  <b>{formatNumber(estimate.hardware.total_cost)}</b>
                </article>
                <article>
                  <div><span className="cost-dot cost-dot--labor" /><div><strong>{estimate.labor.labor_rate_name}</strong><small>{formatNumber(estimate.labor.labor_hours)} hours × {formatNumber(estimate.labor.rate_per_hour)}</small></div></div>
                  <b>{formatNumber(estimate.labor.total_cost)}</b>
                </article>
              </div>
              <div className="cost-equation">
                <span>{formatNumber(estimate.material.total_cost)}</span><i>+</i><span>{formatNumber(estimate.hardware.total_cost)}</span><i>+</i><span>{formatNumber(estimate.labor.total_cost)}</span><i>=</i><strong>{formatNumber(estimate.total_cost)}</strong>
              </div>
              <button className="button button--primary button--wide" onClick={createQuotation} disabled={Boolean(busy)}>
                {busy === "quote" ? <BusyLabel>Saving snapshot…</BusyLabel> : "Create immutable quotation"}
              </button>
            </>
          )}
        </div>
      </div>

      <div className="quotations-section">
        <div className="component-table__heading">
          <div><p className="eyebrow">Saved records</p><h3>Quotations</h3><p>Each record keeps the exact plan, quantities, and prices used at creation.</p></div>
          {quotations.length > 0 && <button className="button button--secondary print-hidden" onClick={() => window.print()}>Print this page</button>}
        </div>
        {quotations.length === 0 ? (
          <div className="quotation-empty">No quotations have been created for this revision.</div>
        ) : (
          <div className="quotation-list">
            {quotations.map((quote) => (
              <article key={quote.id} className="quotation-card">
                <header>
                  <div><small>Quotation</small><strong>{quote.quotation_number}</strong></div>
                  <div className="quotation-card__total"><small>Total cost</small><strong>{formatNumber(quote.total_cost)}</strong></div>
                </header>
                <p>{furniture.name} · Revision {quote.plan_revision} · created {formatDate(quote.created_at)}</p>
                <dl>
                  <div><dt>{quote.wood_material_name}</dt><dd>{formatNumber(quote.wood_material_cost)}</dd></div>
                  <div><dt>{quote.hardware_material_name}</dt><dd>{formatNumber(quote.hardware_cost)}</dd></div>
                  <div><dt>{quote.labor_rate_name}</dt><dd>{formatNumber(quote.labor_cost)}</dd></div>
                </dl>
                <footer>{isDemoCatalogName(quote.wood_material_name) || isDemoCatalogName(quote.labor_rate_name) ? "Demonstration prices · " : ""}Price snapshot locked at creation</footer>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
