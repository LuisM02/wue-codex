import type {
  CompleteCost, CostSelection, Furniture, FurnitureClassification, FurnitureDimensions,
  FurnitureImage, FurniturePlan, FurnitureType, HardwareQuantity, ImageView, LaborQuantity,
  LaborRate, Material, MaterialQuantity, PlanComponent, PlanGeometry, Project, Quotation, UUID,
} from "../types/api";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function extractErrorMessage(payload: unknown): string {
  if (!payload || typeof payload !== "object" || !("detail" in payload)) {
    return "The server could not complete this request.";
  }
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) =>
      item && typeof item === "object" && "msg" in item
        ? String((item as { msg: unknown }).msg)
        : String(item),
    ).join(" · ");
  }
  return "The request contains an invalid value.";
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  headers.set("Accept", "application/json");
  const response = await fetch(`${API_ROOT}${path}`, { ...options, headers });
  if (!response.ok) {
    let payload: unknown;
    try { payload = await response.json(); } catch { payload = null; }
    throw new ApiError(extractErrorMessage(payload), response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function queryString(params: Record<string, string>): string {
  return new URLSearchParams(params).toString();
}

export const api = {
  projects: {
    list: () => request<Project[]>("/projects"),
    create: (payload: { name: string; description?: string | null }) =>
      request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  },
  furniture: {
    list: (projectId: UUID) => request<Furniture[]>(`/projects/${projectId}/furniture`),
    create: (projectId: UUID, payload: { name: string; furniture_type?: FurnitureType }) =>
      request<Furniture>(`/projects/${projectId}/furniture`, { method: "POST", body: JSON.stringify(payload) }),
    update: (furnitureId: UUID, payload: { name?: string; furniture_type?: FurnitureType }) =>
      request<Furniture>(`/furniture/${furnitureId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  },
  images: {
    list: (furnitureId: UUID) => request<FurnitureImage[]>(`/furniture/${furnitureId}/images`),
    contentUrl: (furnitureId: UUID, view: ImageView) => `${API_ROOT}/furniture/${furnitureId}/images/${view}/content`,
    upload: (furnitureId: UUID, view: ImageView, file: File) => {
      const body = new FormData();
      body.append("file", file);
      body.append("source", "upload");
      return request<FurnitureImage>(`/furniture/${furnitureId}/images/${view}`, { method: "POST", body });
    },
    remove: (furnitureId: UUID, view: ImageView) =>
      request<void>(`/furniture/${furnitureId}/images/${view}`, { method: "DELETE" }),
  },
  classification: {
    get: (furnitureId: UUID) => request<FurnitureClassification>(`/furniture/${furnitureId}/classification`),
    run: (furnitureId: UUID) => request<FurnitureClassification>(`/furniture/${furnitureId}/classification`, { method: "POST" }),
  },
  dimensions: {
    get: (furnitureId: UUID) => request<FurnitureDimensions>(`/furniture/${furnitureId}/dimensions`),
    save: (furnitureId: UUID, payload: { width: number; height: number; depth: number; unit: string; source: "manual" }) =>
      request<FurnitureDimensions>(`/furniture/${furnitureId}/dimensions`, { method: "PUT", body: JSON.stringify(payload) }),
  },
  plans: {
    list: (furnitureId: UUID) => request<FurniturePlan[]>(`/furniture/${furnitureId}/plans`),
    generate: (furnitureId: UUID) => request<FurniturePlan>(`/furniture/${furnitureId}/plans`, { method: "POST" }),
    updateComponent: (planId: UUID, componentId: UUID, payload: Partial<PlanComponent>) =>
      request<PlanComponent>(`/plans/${planId}/components/${componentId}`, { method: "PATCH", body: JSON.stringify(payload) }),
    finalize: (planId: UUID) => request<FurniturePlan>(`/plans/${planId}/finalize`, { method: "POST" }),
    revise: (planId: UUID) => request<FurniturePlan>(`/plans/${planId}/revisions`, { method: "POST" }),
    geometry: (planId: UUID) => request<PlanGeometry>(`/plans/${planId}/geometry-3d`),
    materialQuantity: (planId: UUID) => request<MaterialQuantity>(`/plans/${planId}/material-quantity`),
    hardwareQuantity: (planId: UUID) => request<HardwareQuantity>(`/plans/${planId}/hardware-quantity`),
    laborQuantity: (planId: UUID) => request<LaborQuantity>(`/plans/${planId}/labor-quantity`),
  },
  catalog: {
    materials: (type: "wood" | "hardware") =>
      request<Material[]>(`/admin/materials?${queryString({ material_type: type, is_active: "true" })}`),
    laborRates: () => request<LaborRate[]>("/admin/labor-rates?is_active=true"),
  },
  estimates: {
    complete: (planId: UUID, selection: CostSelection) =>
      request<CompleteCost>(`/plans/${planId}/complete-cost?${queryString({ ...selection })}`),
    listQuotations: (planId: UUID) => request<Quotation[]>(`/plans/${planId}/quotations`),
    createQuotation: (planId: UUID, selection: CostSelection) =>
      request<Quotation>(`/plans/${planId}/quotations`, { method: "POST", body: JSON.stringify(selection) }),
  },
};
