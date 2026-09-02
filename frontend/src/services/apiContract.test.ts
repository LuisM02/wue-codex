import { afterEach, describe, expect, it, vi } from "vitest";

import contract from "../../../contracts/frontend-api.json";
import type { PlanComponentPayload } from "../types/api";
import { api } from "./apiClient";

interface Operation {
  method: string;
  path: string;
}

function operationKey(operation: Operation): string {
  return `${operation.method.toUpperCase()} ${operation.path}`;
}

function canonicalPath(rawPath: string): string {
  return new URL(rawPath, "http://wue.test").pathname
    .replaceAll("project-id", "{project_id}")
    .replaceAll("furniture-id", "{furniture_id}")
    .replaceAll("plan-id", "{plan_id}")
    .replaceAll("component-id", "{component_id}")
    .replace(/\/images\/front(?=\/|$)/, "/images/{view}");
}

const component: PlanComponentPayload = {
  component_name: "leg_1",
  component_type: "leg",
  width: "40",
  height: "400",
  depth: "40",
  thickness: null,
  x: "0",
  y: "0",
  z: "0",
  rotation: "0",
  rotation_x: "0",
  rotation_y: "0",
  rotation_z: "0",
  geometry_kind: "box",
  profile_points: null,
  quantity: 1,
  sort_order: 0,
};

describe("frontend/backend API route contract", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("tracks every operation issued by the frontend client", async () => {
    const used: Operation[] = [];
    vi.stubGlobal("fetch", vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
      const rawPath = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      used.push({ method: init?.method ?? "GET", path: canonicalPath(rawPath) });
      return new Response("{}", { status: 200, headers: { "Content-Type": "application/json" } });
    }));

    await Promise.all([
      api.projects.list(),
      api.projects.create({ name: "Project" }),
      api.furniture.list("project-id"),
      api.furniture.create("project-id", { name: "Chair" }),
      api.furniture.update("furniture-id", { furniture_type: "chair" }),
      api.images.list("furniture-id"),
      api.images.upload("furniture-id", "front", new File(["image"], "front.png", { type: "image/png" })),
      api.images.remove("furniture-id", "front"),
      api.classification.get("furniture-id"),
      api.classification.run("furniture-id"),
      api.dimensions.get("furniture-id"),
      api.dimensions.save("furniture-id", { width: 1, height: 1, depth: 1, unit: "mm", source: "manual" }),
      api.reconstruction.get("furniture-id"),
      api.reconstruction.run("furniture-id"),
      api.plans.list("furniture-id"),
      api.plans.generate("furniture-id"),
      api.plans.get("plan-id"),
      api.plans.addComponent("plan-id", component),
      api.plans.updateComponent("plan-id", "component-id", component),
      api.plans.deleteComponent("plan-id", "component-id"),
      api.plans.finalize("plan-id"),
      api.plans.revise("plan-id"),
      api.plans.geometry("plan-id"),
      api.plans.materialQuantity("plan-id"),
      api.plans.hardwareQuantity("plan-id"),
      api.plans.laborQuantity("plan-id"),
      api.catalog.materials("wood"),
      api.catalog.laborRates(),
      api.estimates.complete("plan-id", { material_id: "wood", hardware_material_id: "screw", labor_rate_id: "rate" }),
      api.estimates.listQuotations("plan-id"),
      api.estimates.createQuotation("plan-id", { material_id: "wood", hardware_material_id: "screw", labor_rate_id: "rate" }),
    ]);
    used.push({ method: "GET", path: canonicalPath(api.images.contentUrl("furniture-id", "front")) });

    const actual = [...new Set(used.map(operationKey))].sort();
    const expected = contract.operations.map(operationKey).sort();
    expect(actual).toEqual(expected);
  });
});
