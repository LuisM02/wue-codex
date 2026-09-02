import { describe, expect, it } from "vitest";

import { settledFailureMessage } from "./loadState";

describe("saved-work error summaries", () => {
  it("returns no message when every resource loads", () => {
    expect(settledFailureMessage(["photos"], [{ status: "fulfilled", value: [] }])).toBeNull();
  });

  it("treats an optional missing saved resource as an empty state", () => {
    const missing = Object.assign(new Error("Classification not found"), { status: 404 });
    expect(settledFailureMessage(["recognition"], [{ status: "rejected", reason: missing }])).toBeNull();
  });

  it("names every failed resource without repeating the same reason", () => {
    expect(settledFailureMessage(
      ["photos", "recognition", "dimensions"],
      [
        { status: "rejected", reason: new Error("Server unavailable") },
        { status: "fulfilled", value: null },
        { status: "rejected", reason: new Error("Server unavailable") },
      ],
    )).toBe("Could not load saved photos, dimensions. Server unavailable");
  });
});
