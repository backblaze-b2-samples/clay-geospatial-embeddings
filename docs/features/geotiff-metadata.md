<!-- last_verified: 2026-09-11 -->
# Feature: GeoTIFF metadata

## Purpose
Read the geospatial header of a GeoTIFF tile — CRS, pixel dimensions, band
count, bounds, and ground sample distance (GSD) — for the Imagery Library and to
drive Clay datacube construction. This repurposes the starter's generic
metadata-extraction concept for geospatial rasters.

## Used By
- UI: Imagery Library cards (`/library`)
- API: `GET /library` (metadata), `GET /library/thumbnail`
- Engine: `service/jobs.py` and `service/search.py` read band pixels for embedding

## Core Functions
- `services/api/app/service/geotiff.py` — `read_metadata`, `read_pixels`, `render_thumbnail`
- `services/api/app/types/library.py` — `GeoTiffMetadata`

## Canonical Files
- GeoTIFF reader: `services/api/app/service/geotiff.py`

## Inputs
- data: bytes (a GeoTIFF object body from B2)
- band_count: int (how many bands to read for embedding)

## Outputs
- `GeoTiffMetadata` (width, height, band_count, crs, bounds, gsd, dtype)
- pixels: numpy array (C, H, W) for the Clay datacube
- PNG thumbnail bytes

## Flow
- `rasterio.io.MemoryFile(data)` opens the object in memory (no temp file)
- Header fields read from the dataset; GSD from the affine transform
- Thumbnail: percentile-stretched RGB bands rendered to a small PNG

## Edge Cases
- rasterio not installed → metadata null + warning (never raises for listing); `read_pixels`/thumbnail raise `GeoTiffError`
- Corrupt/unparseable tile → warning, item still lists
- Fewer bands than the preset needs → `GeoTiffError`, tile skipped in a run

## Verification
- Test files: `services/api/tests/test_library_search.py`
- Required cases: item lists with a warning when metadata cannot be read
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Imagery Library](imagery-library.md)
- [Clay Embeddings](clay-embeddings.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
