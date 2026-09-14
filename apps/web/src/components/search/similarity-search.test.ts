import { describe, expect, it } from "vitest";
import type { SearchHit } from "@clay-geospatial-embeddings/shared";

import { dedupeHitsByTileKey } from "./similarity-search";

function hit(tile_key: string, embedding_key: string, score: number): SearchHit {
  return { tile_key, embedding_key, score };
}

describe("dedupeHitsByTileKey", () => {
  it("keeps the first (best-scoring) hit per tile_key", () => {
    const hits = [
      hit("imagery/water-02.tif", "embeddings/job-a/aaa.npy", 0.98),
      hit("imagery/urban-01.tif", "embeddings/job-a/bbb.npy", 0.91),
      // Re-embedded by a later job: same tile, different embedding_key —
      // would render the identical thumbnail URL if not de-duped.
      hit("imagery/water-02.tif", "embeddings/job-b/ccc.npy", 0.87),
    ];

    expect(dedupeHitsByTileKey(hits)).toEqual([
      hit("imagery/water-02.tif", "embeddings/job-a/aaa.npy", 0.98),
      hit("imagery/urban-01.tif", "embeddings/job-a/bbb.npy", 0.91),
    ]);
  });

  it("returns every hit unchanged when tile_key values are already distinct", () => {
    const hits = [
      hit("imagery/water-02.tif", "embeddings/job-a/aaa.npy", 0.98),
      hit("imagery/urban-01.tif", "embeddings/job-a/bbb.npy", 0.91),
    ];

    expect(dedupeHitsByTileKey(hits)).toEqual(hits);
  });

  it("returns an empty array for no hits", () => {
    expect(dedupeHitsByTileKey([])).toEqual([]);
  });
});
