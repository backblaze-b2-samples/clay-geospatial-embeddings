<!-- last_verified: 2026-09-11 -->
# Feature: Imagery Library

## Purpose
A scoped gallery of the GeoTIFF tiles under `imagery/`, with PNG thumbnails and
parsed geospatial metadata — the sample-specific asset explorer, distinct from
the never-removable full-bucket File Browser.

## Used By
- UI: `/library` page, `imagery-gallery.tsx`
- API: `GET /library`, `GET /library/thumbnail?key=...` (returns a PNG, referenced by `<img>`)

## Core Functions
- `services/api/app/service/library.py` — `list_imagery`, `get_thumbnail`
- `services/api/app/service/geotiff.py` — `read_metadata`, `render_thumbnail` (rasterio, lazy)
- `services/api/app/runtime/library.py` — REST handlers
- `apps/web/src/components/library/imagery-gallery.tsx`
- `apps/web/src/lib/queries.ts` — `useLibrary`; `apps/web/src/lib/api-client.ts` — `getLibrary`, `thumbnailUrl`

## Canonical Files
- Library service: `services/api/app/service/library.py`

## Inputs
- limit: int (1–500, default 100)
- key: string (imagery tile key, for thumbnails)

## Outputs
- `GET /library` → `ImageryItem[]` (key, size, geospatial metadata or a warning)
- `GET /library/thumbnail` → `image/png`

## Flow
- Page loads → `GET /library` lists `imagery/` tiles scoped to `.tif/.tiff`, newest first
- Each card shows a thumbnail (`/library/thumbnail`) plus CRS, dimensions, band count, GSD
- "Find similar" deep-links to `/search?key=<tile>`

## Edge Cases
- Geospatial stack not installed → items still list, metadata null with a warning; thumbnail 415 → `<img>` falls back to a placeholder
- Tile too large to parse inline (> 40 MB) → listed without metadata
- Empty `imagery/` → seed/upload prompt

## UX States
- Empty / Loading (skeletons) / Error (retry) / Loaded (grid of cards)

## Verification
- Test files: `services/api/tests/test_library_search.py`
- Required cases: scoping to `.tif/.tiff`, item still lists when metadata is unavailable
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [GeoTIFF Metadata](geotiff-metadata.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
