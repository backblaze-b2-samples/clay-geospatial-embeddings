<!-- last_verified: 2026-08-06 -->
# Architecture

## Components

- **apps/web/** — Next.js 16 frontend (App Router, Tailwind v4, shadcn/ui)
  - Dashboard with archive stats, ingest activity, recent embedding jobs
  - Embedding Jobs (primary entity): create / run / edit / delete
  - Imagery Library (scoped GeoTIFF gallery over `imagery/`)
  - Similarity Search over embeddings
  - Imagery ingest (direct-to-B2 upload) and full-bucket file browser
  - Dark mode via `next-themes`
- **services/api/** — FastAPI backend (layered architecture)
  - REST API for jobs, imagery library, search, upload, listing, deletion
  - B2 S3 integration via boto3
  - Local Clay foundation-model embedding engine (`app/service/clay/`)
  - GeoTIFF metadata + pixel reads and thumbnails (rasterio)
  - Health check endpoint with B2 connectivity verification
  - Structured JSON logging with request tracing
  - Prometheus-format metrics endpoint
- **packages/shared/** — TypeScript type definitions
  - Mirrors Pydantic models from the API
  - Consumed by `apps/web/` as workspace dependency

## Backend Layering

The API follows a strict layered architecture:

```
types/     Pydantic models — no logic, no imports from other layers
  |
config/    Settings (pydantic-settings) — depends only on types
  |
repo/      Data access (boto3 B2 client) — no business logic
  |
service/   Business logic — calls repo, returns types
  |
runtime/   FastAPI routes — calls service, never repo directly
```

### Layering Rules

1. Dependencies flow downward only: `types` -> `config` -> `repo` -> `service` -> `runtime`
2. No backward imports (e.g., service must not import from runtime)
3. `boto3` only allowed in `repo/` layer
4. All boundary data uses Pydantic models (no raw dicts across layers)
5. Authored Python files under `services/api/app/` stay under 300 lines

### Directory Structure

```
services/api/
  main.py                  App entrypoint, middleware, router registration
  app/
    types/                 Pydantic models (FileMetadata, JobRecord, ImageryItem, SearchResponse, ...)
    config/                Settings + B2 key prefixes
    repo/                  B2 S3 client + job_store / embeddings / vector_index (data access)
    service/               Business logic (jobs, clay/, geotiff, library, search, upload, files)
    runtime/               FastAPI route handlers (jobs, library, search, files, upload, health)
  requirements.txt/.lock   Base deps (installed by setup/CI)
  requirements-ml.txt      Gated engine deps (torch, claymodel, rasterio, usearch — NOT in setup/CI)
  scripts/seed_imagery.py  Synthetic GeoTIFF seed generator
  tests/                   pytest tests (structural + integration)
```

## Boundary Invariants

- **No external SDK leakage**: `boto3` is only imported in `app/repo/`. All other layers interact with B2 through the repo interface.
- **No raw dicts at boundaries**: All data crossing layer boundaries uses typed Pydantic models.
- **No cross-layer mutable state**: Configuration is read-only after init, and no mutable state is shared *between* layers. Intra-layer caches/counters (the listing cache in `repo/list_cache.py`, the B2 connectivity cache in `repo/b2_client.py`, the download counter in `repo/counter.py`, the rate-limit and metrics state in `runtime/`) are module-local and guarded by a `threading.Lock`. The listing cache also owns the only background thread in the app: a stale entry is served immediately while that thread re-scans (stale-while-revalidate), and `main.lifespan` warms it once at startup so no user pays for the cold full-bucket scan.
- **Validated inputs**: All HTTP inputs validated by FastAPI/Pydantic. File keys reject empty and path-traversal patterns; optional prefix confinement via `ALLOWED_KEY_PREFIX` (off by default).

## Deployment

- **Local dev** — `pnpm dev` runs both services via `concurrently`
  - Web: `localhost:3000`
  - API: `localhost:8000`
- **Railway** — two services from the same repository: `web` builds from the
  repository root because it consumes `packages/shared`; `api` builds from
  `services/api`. Each service's versioned config sits at its own root —
  `railway.json` and `services/api/railway.json` — the default path Railway
  discovers, so a one-click template deploy inherits the same build, start, and
  health behavior with nothing to configure by hand. The human-approved
  staging/production contract lives in [infra/railway/README.md](infra/railway/README.md).
- **Vercel** — one project using [Vercel Services](https://vercel.com/docs/services):
  the `web` (Next.js) and `api` (FastAPI) services build from the same repo and
  share one origin — the web app at `/`, the API under `/api`. The repo-root
  `vercel.json` declares both services and routes `/api/*` to the API service;
  the Vercel-only `services/api/index.py` strips the `/api` prefix so FastAPI
  keeps its native paths (`/health`, `/files`, …). Uploads go directly from the
  browser to B2 via a presigned PUT (see
  [File Upload](docs/features/file-upload.md)), so they bypass the Function's
  4.5 MB payload ceiling entirely — the bucket must allow the deploy origin in
  its CORS. A two-separate-Projects alternative and the full delivery contract
  live in [infra/vercel/README.md](infra/vercel/README.md).

External provisioning and deployment remain explicit user-approved actions.

## Data Stores

- **Backblaze B2** — object storage (S3-compatible API), the sole data store
  - `imagery/` — raw/ingested GeoTIFF tiles
  - `tiles/` — normalized tile cache (reserved)
  - `embeddings/<job_id>/<hash>.npy` — Clay embedding tensors
  - `jobs/<id>.json` — Embedding Job records (no database)
  - Region-derived endpoint (`https://s3.<B2_REGION>.backblazeb2.com`); no region hardcoded in source

## External Services

- **Backblaze B2 S3 API** — file storage, retrieval, deletion, presigned URLs

## Trust Boundaries

See [docs/SECURITY.md](docs/SECURITY.md) for full security documentation.

- **Frontend -> API** — CORS-restricted to configured origins. `CORSMiddleware` is registered LAST in `main.py` (outermost) so it wraps **every** response, including uncaught-exception 500s — otherwise the browser would block error responses and the UI would only see an opaque "network error". See [docs/RELIABILITY.md](docs/RELIABILITY.md#error-handling). A per-IP rate-limit middleware sits inner to CORS; see [docs/SECURITY.md](docs/SECURITY.md#rate-limiting).
- **API -> B2** — authenticated via application keys, signature v4
- **Client -> B2** — presigned URLs for download (10-min expiry, forced attachment)

## Data Flows

- **Ingest**: Browser -> `POST /upload/presign` (validates + signs a PUT) -> Browser PUTs bytes **directly to B2** under `imagery/` -> `POST /upload/verify` -> response
- **Embed (run a job)**: Browser -> `POST /jobs/{id}/run` -> service lists tiles under the source prefix, `get_object` each, reads pixels (rasterio), runs Clay on the autodetected device, writes `.npy` to `embeddings/<id>/`, updates the job record
- **Search**: Browser -> `POST /search` -> service embeds the query tile with Clay -> `repo/vector_index` builds a usearch index over `embeddings/` from B2 -> returns ranked hits
- **List / Library**: Browser -> `GET /files` or `GET /library` -> service calls repo -> returns file list / imagery items with metadata
- **Delete**: Browser -> `DELETE /jobs/{id}` -> scoped delete of `embeddings/<id>/` + `jobs/<id>.json`; `DELETE /files-by-key?key=` for arbitrary objects

## Observability

- Structured JSON logging on all requests with `request_id`
- Request timing middleware (logs duration per request; also the catch-all that converts uncaught exceptions to a typed JSON 500)
- `/metrics` endpoint (Prometheus format: request count, latency, upload count)
- `/health` endpoint (B2 connectivity check)

## API Contract

- Checked-in OpenAPI artifact: `docs/api/openapi.json`
- Export/check command: `pnpm contract:export` / `pnpm contract:check`
- FastAPI freshness test: `services/api/tests/test_openapi_contract.py`
- Frontend route drift test: `apps/web/src/lib/api-contract.test.ts`

The frontend client keeps a small `API_CLIENT_ROUTES` registry in
`apps/web/src/lib/api-client.ts`. Tests compare that registry to the checked-in
OpenAPI artifact so route changes fail loudly before the hand-written client can
silently drift from FastAPI. `GET /metrics` is intentionally server-only.

## Canonical Files

- Layered API handler: `services/api/app/runtime/upload.py`
- Service orchestration: `services/api/app/service/upload.py`
- B2 data access (repo layer): `services/api/app/repo/b2_client.py`
- Pydantic models: `services/api/app/types/` (`files.py`, `upload.py`, `stats.py`, `formatting.py`)
- Config (pydantic-settings): `services/api/app/config/settings.py`
- Structural tests: `services/api/tests/test_structure.py`
- OpenAPI contract: `docs/api/openapi.json`
- OpenAPI exporter: `services/api/scripts/export_openapi.py`
- Frontend API client: `apps/web/src/lib/api-client.ts`
- Shared TypeScript types: `packages/shared/src/types.ts`

## Local ML engine

The headline capability runs Clay's own model (`app/service/clay/`). Its heavy,
native dependency closure (torch, `claymodel`, rasterio, usearch) is **gated in
`requirements-ml.txt`** and excluded from `pnpm run setup` and CI, so the base
verify path stays fast and hermetic. Every engine module imports those libraries
lazily; without them the app still boots, tests pass, and a run/search records an
actionable "engine not installed" state instead of a 500.

Device selection is runtime autodetect **CUDA → Apple MPS → CPU, defaulting to
CPU** (`service/clay/engine.py::select_device`). `PYTORCH_ENABLE_MPS_FALLBACK=1`
is set before torch imports, and an MPS/CUDA embed that still fails is retried on
CPU (`service/jobs.py`), so partial MPS op coverage never blocks a run. Override
with `CLAY_DEVICE`.

## Core Features

- [Embedding Jobs](docs/features/embedding-jobs.md)
- [Clay Embeddings](docs/features/clay-embeddings.md)
- [Imagery Library](docs/features/imagery-library.md)
- [Similarity Search](docs/features/similarity-search.md)
- [GeoTIFF Metadata](docs/features/geotiff-metadata.md)
- [Imagery Ingest](docs/features/file-upload.md)
- [File Browser](docs/features/file-browser.md)
- [Dashboard](docs/features/dashboard.md)

## References

- [docs/SECURITY.md](docs/SECURITY.md) — security principles and implementation
- [docs/RELIABILITY.md](docs/RELIABILITY.md) — reliability expectations
- [AGENTS.md](AGENTS.md) — architectural invariants and agent instructions
