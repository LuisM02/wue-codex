import { describe, expect, it } from "vitest";

import { canOpenStep, completedSteps, nextStep, type WorkflowContext } from "./workflow";

const project = { id: "p", name: "Project", description: null, created_at: "", updated_at: "" };
const furniture = { id: "f", project_id: "p", name: "Chair", furniture_type: "chair" as const, created_at: "", updated_at: "" };
const classification = { id: "c", furniture_id: "f", predicted_type: "chair" as const,
  classifier_name: "test", classifier_version: "1", confidence: "0.7", input_signature: "sig", created_at: "", updated_at: "" };

function context(overrides: Partial<WorkflowContext> = {}): WorkflowContext {
  return { project: null, furniture: null, classification: null, images: [], dimensions: null, plan: null, bomSelection: null, ...overrides };
}

describe("workflow access", () => {
  it("only opens piece selection before a furniture item exists", () => {
    const empty = context();
    expect(canOpenStep("project", empty)).toBe(true);
    expect(canOpenStep("photos", empty)).toBe(false);
  });

  it("keeps measurements locked until an uploaded piece is classified", () => {
    const unclassified = { ...furniture, furniture_type: null };
    const images = ["front", "back", "left", "right", "top"].map((view, index) => ({
      id: String(index), furniture_id: "f", view: view as "front", source: "upload" as const,
      original_filename: "x.jpg", content_type: "image/jpeg", file_size_bytes: 1,
      checksum_sha256: "x", pixel_width: 1, pixel_height: 1, created_at: "", updated_at: "",
      object_left_ratio: "0", object_top_ratio: "0", object_width_ratio: "1", object_height_ratio: "1", is_mirrored: false,
    }));

    expect(canOpenStep("dimensions", context({ project, furniture: unclassified, images }))).toBe(false);
  });

  it("requires exactly the five saved views before dimensions", () => {
    const base = context({ project, furniture });
    expect(canOpenStep("photos", base)).toBe(true);
    expect(canOpenStep("dimensions", base)).toBe(false);
    const images = ["front", "back", "left", "right", "top"].map((view, index) => ({
      id: String(index), furniture_id: "f", view: view as "front", source: "upload" as const,
      original_filename: "x.jpg", content_type: "image/jpeg", file_size_bytes: 1,
      checksum_sha256: "x", pixel_width: 1, pixel_height: 1, created_at: "", updated_at: "",
      object_left_ratio: "0", object_top_ratio: "0", object_width_ratio: "1", object_height_ratio: "1", is_mirrored: false,
    }));
    expect(canOpenStep("dimensions", { ...base, images })).toBe(false); // Manual type is not recognition.
    expect(canOpenStep("dimensions", { ...base, images, classification })).toBe(true);
    expect(canOpenStep("dimensions", { ...base, images, classification: { ...classification, furniture_id: "other" } })).toBe(false);
    expect(canOpenStep("dimensions", { ...base, images, classification: { ...classification, predicted_type: "bookshelf" } })).toBe(false);
    expect(canOpenStep("dimensions", { ...base, images: [...images.slice(0, 4), images[0]], classification })).toBe(false);
  });

  it("blocks new planning with saved dimensions but no accepted recognition", () => {
    const dimensions = { id: "d", furniture_id: "f", width_mm: "450", height_mm: "900", depth_mm: "500",
      unit: "mm" as const, source: "manual" as const, is_locked: false, locked_at: null, created_at: "", updated_at: "" };
    expect(canOpenStep("plan", context({ project, furniture, dimensions }))).toBe(false);
  });

  it("opens preview and BOM for a finalized plan, then costing after BOM selection", () => {
    const draft = context({ project, furniture, plan: {
      id: "plan", furniture_id: "f", revision: 1, status: "draft", furniture_type: "chair", source_reconstruction_id: null,
      parts_reviewed_at: null,
      components: [], created_at: "", updated_at: "",
    } });
    expect(canOpenStep("model", draft)).toBe(false);
    const finalized = { ...draft, plan: { ...draft.plan!, status: "finalized" as const } };
    expect(canOpenStep("model", finalized)).toBe(true);
    expect(canOpenStep("plan", finalized)).toBe(true); // Historical design inspection is preserved.
    expect(canOpenStep("bom", finalized)).toBe(true);
    expect(canOpenStep("estimate", finalized)).toBe(false);
    expect(completedSteps(finalized)).toEqual(new Set(["project", "plan", "model"]));
    const reviewed = {
      ...finalized,
      bomSelection: { material_id: "wood", hardware_material_id: "screw" },
    };
    expect(canOpenStep("estimate", reviewed)).toBe(true);
    expect(completedSteps(reviewed)).toEqual(new Set(["project", "plan", "model", "bom"]));
  });

  it("returns the next unlocked step", () => {
    const active = context({ project, furniture });
    expect(nextStep("project", active)).toBe("photos");
  });
});
