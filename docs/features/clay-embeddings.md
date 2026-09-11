<!-- last_verified: 2026-09-11 -->
# Feature: Local Clay foundation-model embedding

## Purpose
Turn imagery tiles into geospatial embedding vectors by running Clay's **own**
model on-device (never a substitute), writing `.npy` tensors to B2.

## Used By
- UI: indirectly, via Embedding Jobs (`/jobs/[id]` Run) and Similarity Search
- API: `POST /jobs/{job_id}/run`, `POST /search`
- Engine: `services/api/app/service/clay/`

## Core Functions
- `services/api/app/service/clay/engine.py` — `select_device`, `_load_model` (Clay v1.5 from HuggingFace `made-with-clay/Clay`), `embed_pixels`, `EngineUnavailableError`
- `services/api/app/service/clay/datacube.py` — builds the Clay datacube (pixels, waves, gsd, time, latlon)
- `services/api/app/service/clay/presets.py` — Sentinel-2 RGB / Sentinel-2 L2A / NAIP RGB band presets
- `services/api/app/repo/embeddings.py` — `.npy` read/write in B2

## Canonical Files
- Engine: `services/api/app/service/clay/engine.py`

## Inputs
- pixels: numpy array (C, H, W) read from a GeoTIFF via rasterio
- preset: sensor band definition (wavelengths, gsd, normalization)

## Outputs
- embedding vector: `float32` numpy array (Clay v1.5 encoder class token), stored as `.npy`

## Device rule (hard)
- Autodetect **CUDA → Apple MPS → CPU**, defaulting to **CPU**.
- `PYTORCH_ENABLE_MPS_FALLBACK=1` is set before torch imports; an MPS/CUDA embed
  that still fails is retried once on CPU (`service/jobs.py`). Override with
  `CLAY_DEVICE=auto|cpu|cuda|mps`.

## Install / cost
- torch + `claymodel` are gated in `services/api/requirements-ml.txt` (not in
  base setup/CI). Install with `pnpm run setup:ml`. Clay v1.5 weights are public
  (no `HF_TOKEN`). A full local demo run costs **$0** (local compute only).

## Edge Cases
- ML stack missing → `EngineUnavailableError` → job/search reports an actionable message, process stays alive
- Tile band count < preset band count → tile skipped with a warning
- MPS unsupported op → CPU fallback

## Verification
- Test files: `services/api/tests/test_library_search.py` (engine degradation), `services/api/tests/test_jobs.py`
- Required cases: device selection contained without torch; run/search fail gracefully without the ML stack
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green; a live embed run produces `.npy` artifacts in B2

## Related Docs
- [Embedding Jobs](embedding-jobs.md)
- [Similarity Search](similarity-search.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
