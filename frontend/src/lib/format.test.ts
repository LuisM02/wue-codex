import { describe, expect, it } from "vitest";

import { formatFileSize, furnitureLabel, unitLabel } from "./format";

describe("display formatting", () => {
  it("uses friendly closed-domain labels", () => {
    expect(furnitureLabel("dining_table")).toBe("Dining table");
    expect(unitLabel("mm3")).toBe("mm³");
  });

  it("formats image file sizes", () => {
    expect(formatFileSize(1024)).toContain("KB");
    expect(formatFileSize(2 * 1024 * 1024)).toContain("MB");
  });
});
