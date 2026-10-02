import type { FurnitureType } from "../../types/api";

interface Props {
  furnitureType: FurnitureType;
}

/** Display guidance only; it never alters an estimate or its saved snapshot. */
export function QuoteLimitations({ furnitureType }: Props) {
  return (
    <aside className="quote-limitations" aria-label="Prototype estimate limitations">
      <strong>Prototype estimate · review before purchasing or construction</strong>
      <p>Wood-only costing. Net modeled volume excludes cutting waste and stock layout. Hardware and labor use prototype assumptions, not a complete joinery schedule or measured workshop time.</p>
      {furnitureType === "dining_table" && (
        <p>Table rules do not separately itemize apron joints, apron fasteners or apron labor.</p>
      )}
      <p>No tax, markup, overhead or currency is assigned. A correct sum does not verify physical dimensions, manufacturing accuracy or structural safety.</p>
    </aside>
  );
}
