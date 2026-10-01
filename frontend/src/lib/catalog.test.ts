import { describe, expect, it } from "vitest";

import { isDemoCatalogName, isWoodScrewMaterial } from "./catalog";
import type { Material } from "../types/api";

function hardware(name: string): Material {
  return {
    id: "material",
    material_name: name,
    material_type: "hardware",
    unit: "piece",
    is_active: true,
    created_at: "",
    updated_at: "",
  };
}

describe("costing catalog compatibility", () => {
  it("recognizes clearly prefixed demo resources", () => {
    expect(isDemoCatalogName(" DEMO wood - sample price ")).toBe(true);
    expect(isDemoCatalogName("demo labor - sample price")).toBe(true);
  });

  it("does not label ordinary or missing resource names as demo prices", () => {
    expect(isDemoCatalogName(undefined)).toBe(false);
    expect(isDemoCatalogName("Wood screw")).toBe(false);
    expect(isDemoCatalogName("Demolition wood")).toBe(false);
  });

  it("accepts the backend wood-screw identity without case sensitivity", () => {
    expect(isWoodScrewMaterial(hardware(" Wood Screw "))).toBe(true);
  });

  it("rejects other active hardware", () => {
    expect(isWoodScrewMaterial(hardware("Drawer pull"))).toBe(false);
  });
});
