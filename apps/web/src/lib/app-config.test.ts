import { describe, expect, it } from "vitest";
import { APP_DESCRIPTION, APP_NAME } from "@/lib/app-config";

describe("app identity", () => {
  it("ships the canonical app name and description", () => {
    expect(APP_NAME).toBe("Clay Geospatial Embeddings");
    expect(APP_DESCRIPTION).toBe(
      "Run the Clay foundation model locally over satellite imagery in Backblaze B2 — embed, index, and search geospatial scenes"
    );
  });
});
