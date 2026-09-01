import { describe, expect, it } from "vitest";

import { isWoodScrewMaterial } from "./catalog";
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
  it("accepts the backend wood-screw identity without case sensitivity", () => {
    expect(isWoodScrewMaterial(hardware(" Wood Screw "))).toBe(true);
  });

  it("rejects other active hardware", () => {
    expect(isWoodScrewMaterial(hardware("Drawer pull"))).toBe(false);
  });
});
