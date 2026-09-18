import { describe, expect, it } from "vitest";

import { canOpenStep, completedSteps, nextStep, type WorkflowContext } from "./workflow";

const project = { id: "p", name: "Project", description: null, created_at: "", updated_at: "" };
const furniture = { id: "f", project_id: "p", name: "Chair", furniture_type: "chair" as const, created_at: "", updated_at: "" };

function context(overrides: Partial<WorkflowContext> = {}): WorkflowContext {
  return { project: null, furniture: null, images: [], dimensions: null, plan: null, bomSelection: null, ...overrides };
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
    }));
    expect(canOpenStep("dimensions", { ...base, images })).toBe(true);
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
