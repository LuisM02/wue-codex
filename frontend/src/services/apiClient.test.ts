import { describe, expect, it } from "vitest";

import { extractErrorMessage, queryString } from "./apiClient";

describe("API client helpers", () => {
  it("extracts FastAPI string errors", () => {
    expect(extractErrorMessage({ detail: "Plan must be finalized" })).toBe("Plan must be finalized");
  });

  it("combines validation messages", () => {
    expect(extractErrorMessage({ detail: [{ msg: "Width must be positive" }, { msg: "Depth is required" }] }))
      .toBe("Width must be positive · Depth is required");
  });

  it("encodes cost selections as query parameters", () => {
    expect(queryString({ material_id: "wood one", hardware_material_id: "screw", labor_rate_id: "standard" }))
      .toBe("material_id=wood+one&hardware_material_id=screw&labor_rate_id=standard");
  });
});
