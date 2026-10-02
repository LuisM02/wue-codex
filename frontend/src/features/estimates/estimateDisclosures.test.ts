import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import type { Furniture, FurniturePlan, FurnitureType, Quotation } from "../../types/api";
import { EstimatePanel } from "./EstimatePanel";
import { QuoteLimitations } from "./QuoteLimitations";
import { QuotationCard } from "./QuotationCard";

const quote: Quotation = {
  id: "quote", quotation_number: "WUE-SAVED", project_id: "project", furniture_id: "furniture",
  plan_id: "plan", plan_revision: 1, furniture_type: "dining_table",
  wood_material_name: "DEMO wood - sample price", wood_price_per_unit: "100",
  wood_price_unit: "board_ft", wood_quantity: "53.3551294176864", wood_material_cost: "5335.51294176864",
  hardware_material_name: "Wood screw", hardware_price_per_piece: "2", hardware_quantity: 8,
  hardware_cost: "16", labor_rate_name: "DEMO labor - sample price", labor_rate_per_hour: "150",
  labor_hours: "3.2", labor_cost: "480", total_cost: "5831.51294176864",
  created_at: "2026-09-30T12:00:00Z", updated_at: "2026-09-30T12:00:00Z",
};

function card(value = quote) {
  return renderToStaticMarkup(createElement(QuotationCard, { quote: value, furnitureName: "Saved table" }));
}

describe("Cost estimate disclosures", () => {
  it.each(["chair", "dining_table", "bookshelf"] as FurnitureType[])("discloses prototype limits for %s even with real prices", (furnitureType) => {
    const markup = renderToStaticMarkup(createElement(QuoteLimitations, { furnitureType }));
    expect(markup).toContain('aria-label="Prototype estimate limitations"');
    expect(markup).toContain("Wood-only costing");
    expect(markup).toContain("excludes cutting waste and stock layout");
    expect(markup).toContain("not a complete joinery schedule or measured workshop time");
    expect(markup).toContain("No tax, markup, overhead or currency");
    expect(markup).toContain("structural safety");
    expect(markup.includes("apron fasteners")).toBe(furnitureType === "dining_table");
    expect(markup).not.toContain('class="notice');
  });

  it("shows limitations before calculation/catalog loading", () => {
    const markup = renderToStaticMarkup(createElement(EstimatePanel, {
      furniture: { id: "furniture", name: "Table" } as Furniture,
      plan: { id: "plan", revision: 1, furniture_type: "dining_table", components: [] } as unknown as FurniturePlan,
      initialSelection: null,
    }));
    expect(markup).toContain("Build the prototype estimate");
    expect(markup).toContain("Prototype estimate limitations");
    expect(markup).not.toContain("Exact total");
  });

  it("renders quantities, rates, sample-price notice and limits from the immutable quote without modifying it", () => {
    const before = JSON.stringify(quote);
    const markup = card();
    expect(markup).toContain("53.36 board ft × 100");
    expect(markup).toContain("8 pieces × 2");
    expect(markup).toContain("3.2 assumed hours × 150");
    expect(markup).toContain("5,831.51");
    expect(markup).toContain("Demonstration prices");
    expect(markup).toContain("Price snapshot locked at creation");
    expect(markup).toContain("apron labor");
    expect(JSON.stringify(quote)).toBe(before);
  });

  it("keeps real-priced saved quotes provisional and does not falsely mark them as sample prices", () => {
    const markup = card({ ...quote, wood_material_name: "Supplier stock", labor_rate_name: "Workshop rate", furniture_type: "chair" });
    expect(markup).not.toContain("Demonstration prices");
    expect(markup).not.toContain("apron labor");
    expect(markup).toContain("Calculated subtotal");
    expect(markup).toContain("Prototype estimate limitations");
  });

  it("uses each saved quote's own rates, quantity and type rather than current selections", () => {
    const markup = card({ ...quote, wood_price_unit: "m3", wood_quantity: "2", wood_price_per_unit: "7", hardware_quantity: 3, hardware_price_per_piece: "4", labor_hours: "6", labor_rate_per_hour: "8", furniture_type: "bookshelf" });
    expect(markup).toContain("2 m³ × 7");
    expect(markup).toContain("3 pieces × 4");
    expect(markup).toContain("6 assumed hours × 8");
    expect(markup).not.toContain("apron fasteners");
    expect(markup).not.toContain("53.36 board ft");
  });

  it("keeps the dedicated limitations and saved assumptions visible in print styling", async () => {
    const fs = await vi.importActual<{ readFileSync(path: URL, encoding: "utf8"): string }>("node:fs");
    const css = fs.readFileSync(new URL("../../styles.css", import.meta.url), "utf8");
    const print = css.slice(css.indexOf("@media print"));
    expect(print).toContain(".quote-limitations { display: block !important");
    expect(print).toContain(".quotation-card dt small { color: #222; font-size: 10pt; }");
    expect(print).toContain(".quotation-list { grid-template-columns: 1fr;");
    expect(print).not.toMatch(/[^{}]*quote-limitations[^{}]*\{[^}]*display:\s*none/);
  });
});
