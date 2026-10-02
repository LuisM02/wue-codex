import { isDemoCatalogName } from "../../lib/catalog";
import { formatDate, formatNumber, unitLabel } from "../../lib/format";
import type { Quotation } from "../../types/api";
import { QuoteLimitations } from "./QuoteLimitations";

interface Props {
  quote: Quotation;
  furnitureName: string;
}

export function QuotationCard({ quote, furnitureName }: Props) {
  const usesDemoPrices = isDemoCatalogName(quote.wood_material_name)
    || isDemoCatalogName(quote.labor_rate_name);

  return (
    <article className="quotation-card">
      <header>
        <div><small>Saved cost estimate</small><strong>{quote.quotation_number}</strong></div>
        <div className="quotation-card__total"><small>Calculated subtotal</small><strong>{formatNumber(quote.total_cost)}</strong></div>
      </header>
      <p>{furnitureName} · Revision {quote.plan_revision} · created {formatDate(quote.created_at)}</p>
      <dl>
        <div><dt>{quote.wood_material_name}<small>{formatNumber(quote.wood_quantity)} {unitLabel(quote.wood_price_unit)} × {formatNumber(quote.wood_price_per_unit)}</small></dt><dd>{formatNumber(quote.wood_material_cost)}</dd></div>
        <div><dt>{quote.hardware_material_name}<small>{quote.hardware_quantity} pieces × {formatNumber(quote.hardware_price_per_piece)}</small></dt><dd>{formatNumber(quote.hardware_cost)}</dd></div>
        <div><dt>{quote.labor_rate_name}<small>{formatNumber(quote.labor_hours)} assumed hours × {formatNumber(quote.labor_rate_per_hour)}</small></dt><dd>{formatNumber(quote.labor_cost)}</dd></div>
      </dl>
      <QuoteLimitations furnitureType={quote.furniture_type} />
      <footer>{usesDemoPrices ? "Demonstration prices · " : ""}Price snapshot locked at creation</footer>
    </article>
  );
}
