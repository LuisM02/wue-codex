import type { Material } from "../types/api";

export function isDemoCatalogName(name: string | undefined): boolean {
  return name?.trim().toUpperCase().startsWith("DEMO ") ?? false;
}

export function isWoodScrewMaterial(material: Material): boolean {
  return material.material_type === "hardware"
    && material.unit === "piece"
    && material.is_active
    && material.material_name.trim().toLocaleLowerCase() === "wood screw";
}
