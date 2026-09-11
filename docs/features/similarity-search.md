<!-- last_verified: 2026-09-11 -->
# Feature: Similarity search over embeddings

## Purpose
"Find scenes like this one": pick a query tile, embed it with Clay, and retrieve
the nearest neighbours across the archive with a usearch k-NN index built over
the `.npy` embeddings in B2.

## Used By
- UI: `/search` page, `similarity-search.tsx` (deep-linkable via `?key=`)
- API: `POST /search`

## Core Functions
- `services/api/app/service/search.py` — `search_by_key`, `SearchUnavailableError`
- `services/api/app/repo/vector_index.py` — `build_index`, `VectorIndex.query` (usearch, lazy)
- `services/api/app/runtime/search.py` — REST handler
- `apps/web/src/lib/queries.ts` — `useSearch`; `apps/web/src/lib/api-client.ts` — `searchByKey`

## Canonical Files
- Search service: `services/api/app/service/search.py`

## Inputs
- query_key: string (an imagery tile to embed)
- k: int (1–50, default 6)
- sensor: preset used to embed the query

## Outputs
- `SearchResponse` → `{ query_key, index_size, hits: [{ tile_key, embedding_key, score }] }` (cosine similarity, most similar first)

## Flow
- Embed the query tile with Clay on the autodetected device
- Build a fresh usearch index over every `.npy` under `embeddings/` (loaded from B2)
- Return the top-k, mapping each embedding back to its source tile via job records

## Edge Cases
- No embeddings yet → 409 with "run an Embedding Job first"
- ML stack missing → 503 with the install hint
- Unreadable query tile → 400

## UX States
- Query form (tile selector + sensor + k) / Searching / Results grid with score bars / No matches

## Verification
- Test files: `services/api/tests/test_library_search.py`
- Required cases: actionable error when the archive has no embeddings
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green; a live search returns ranked, same-class neighbours over the seed set

## Related Docs
- [Clay Embeddings](clay-embeddings.md)
- [Embedding Jobs](embedding-jobs.md)
- [App Workflows](../app-workflows.md)
