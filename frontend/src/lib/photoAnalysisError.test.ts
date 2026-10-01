import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";

import { ApiError } from "../services/apiClient";
import { photoAnalysisError } from "./photoAnalysisError";
import { ImageWorkspace } from "../features/images/ImageWorkspace";
import type { Furniture, FurnitureImage } from "../types/api";

describe("Photo analysis failures", () => {
  it("keeps the missing-shelf reason and does not blame service availability", () => {
    const result = photoAnalysisError(new ApiError("No reliable internal shelf boundaries", 422));
    expect(result).toContain("No reliable internal shelf boundaries");
    expect(result).toContain("entered dimensions");
    expect(result).toContain("not generated a generic replacement");
    expect(result).not.toContain("not connected yet");
  });

  it.each([503, 504])("distinguishes unavailable/timeout service status %s", (status) => {
    const result = photoAnalysisError(new ApiError("SAM checkpoint could not load", status));
    expect(result).toContain("SAM checkpoint could not load");
    expect(result).toContain("local AI service");
    expect(result).toContain("does not restore photo reconstruction");
    expect(result).not.toContain("not connected yet");
  });

  it("treats invalid geometry as a service result problem", () => {
    expect(photoAnalysisError(new ApiError("Invalid geometry", 502)))
      .toContain("Existing saved drawings have not been replaced");
  });

  it("keeps prerequisite instructions separate", () => {
    expect(photoAnalysisError(new ApiError("Missing top", 409))).toContain("Complete the required photos");
  });

  it("keeps unrelated endpoint errors unchanged", () => {
    expect(photoAnalysisError(new ApiError("Furniture not found", 404))).toBe("Furniture not found");
  });

  it("adds connection guidance to a failed fetch", () => {
    expect(photoAnalysisError(new TypeError("Failed to fetch"))).toContain("WUE is running and reachable");
  });

  it("labels manual classification honestly without claiming the provider is disconnected", () => {
    const markup = renderToStaticMarkup(createElement(ImageWorkspace, {
      furniture: { id: "test", name: "Bookshelf", furniture_type: null } as Furniture,
      images: ["front", "back", "left", "right", "top"].map((view) => ({
        id: view, view, pixel_width: 100, pixel_height: 100, file_size_bytes: 100,
      })) as FurnitureImage[], classification: null,
      onImages() {}, onClassification() {}, onFurniture() {}, onContinue() {},
    }));
    expect(markup).toContain("manual selection, not an AI result");
    expect(markup).not.toContain("provider is not connected yet");
  });
});
