import type { FurnitureType, MaterialUnit } from "../types/api";

const furnitureLabels: Record<FurnitureType, string> = {
  chair: "Chair",
  dining_table: "Dining table",
  bookshelf: "Bookshelf",
};

const unitLabels: Record<MaterialUnit, string> = {
  mm3: "mm³",
  cm3: "cm³",
  m3: "m³",
  board_ft: "board ft",
  piece: "piece",
};

export function furnitureLabel(type: FurnitureType): string {
  return furnitureLabels[type];
}

export function unitLabel(unit: MaterialUnit): string {
  return unitLabels[unit];
}

export function formatNumber(value: string | number, digits = 2): string {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return "—";
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: digits }).format(parsed);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${formatNumber(bytes / 1024, 1)} KB`;
  return `${formatNumber(bytes / (1024 * 1024), 1)} MB`;
}
