import { describe, expect, it } from "vitest";
import { analysisMatchesPlan } from "./analysisProvenance";

const analysis = {
  id: "analysis", furniture_id: "table", furniture_type: "dining_table" as const,
  parts: [{ id: "top" }, { id: "leg" }],
};
const source = {
  source_reconstruction_part_id: "top", source_confidence: "0.68", source_views: ["front" as const],
};
const manual = { source_reconstruction_part_id: null, source_confidence: null, source_views: [] };
const plan = {
  source_reconstruction_id: "analysis", furniture_id: "table", furniture_type: "dining_table" as const,
  components: [source, { ...source, source_reconstruction_part_id: "leg" }],
};

describe("analysis notes provenance", () => {
  it("matches a plan to its actual source parts", () => {
    expect(analysisMatchesPlan(analysis, plan)).toBe(true);
  });
  it("allows manual additions without equating proposal and reviewed part counts", () => {
    expect(analysisMatchesPlan(analysis, { ...plan, components: [...plan.components, manual] })).toBe(true);
  });
  it("rejects re-analysis that reuses the record ID but replaces source parts", () => {
    expect(analysisMatchesPlan({ ...analysis, parts: [{ id: "new-top" }] }, plan)).toBe(false);
  });
  it("rejects deleted source links with retained photo provenance", () => {
    expect(analysisMatchesPlan(analysis, {
      ...plan, components: [{ ...source, source_reconstruction_part_id: null }],
    })).toBe(false);
  });
  it("requires every remaining sourced component to match", () => {
    expect(analysisMatchesPlan(analysis, {
      ...plan, components: [source, { ...source, source_reconstruction_part_id: "old-leg" }],
    })).toBe(false);
  });
  it("rejects other furniture, types, or analysis identities", () => {
    expect(analysisMatchesPlan({ ...analysis, furniture_id: "other-table" }, plan)).toBe(false);
    expect(analysisMatchesPlan({ ...analysis, furniture_type: "chair" }, plan)).toBe(false);
    expect(analysisMatchesPlan({ ...analysis, id: "other-analysis" }, plan)).toBe(false);
  });
  it("does not claim provenance for legacy or wholly manual drawings", () => {
    expect(analysisMatchesPlan(analysis, { ...plan, source_reconstruction_id: null })).toBe(false);
    expect(analysisMatchesPlan(analysis, { ...plan, components: [manual] })).toBe(false);
  });
  it("can show an analysis before a drawing exists", () => {
    expect(analysisMatchesPlan(analysis, null)).toBe(true);
  });
});
