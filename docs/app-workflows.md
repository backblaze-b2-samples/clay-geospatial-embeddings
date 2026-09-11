<!-- last_verified: 2026-09-11 -->
# App Workflows

User journeys inside the application.

## Create and run an Embedding Job (primary flow)

- User navigates to `/jobs` and clicks **New job**
- The create form uses selectors for finite fields (tile size 256/512, model Clay v1.5, sensor preset, source prefix discovered from `imagery/`) and free text only for the name, with safe-default hints (`e.g. sentinel2-tirana-2024`, `imagery/`, 256, Sentinel-2 RGB)
- Submitting writes `jobs/<id>.json` to B2 with status `pending` and lands on the job detail page
- **Run**: the detail page's Run button streams every tile under the source prefix from B2, reads its pixels (rasterio), embeds each with Clay on the autodetected device (CUDA → MPS → CPU), and writes `.npy` embeddings to `embeddings/<id>/`. A CPU run over the seed set takes a minute or two; the page shows an in-progress alert and updates when it finishes
- **Result**: status becomes `succeeded` with a per-run message (tiles embedded, device used, duration) and an embeddings table, or `failed` with an actionable message (e.g. "install requirements-ml.txt", "no tiles under prefix") — the API process never crashes on a native-ML failure
- **Edit**: rename or reconfigure while the job is not running
- **Delete**: removes the job record and only its own `embeddings/<id>/` — imagery is untouched
- See: [Embedding Jobs](features/embedding-jobs.md), [Clay Embeddings](features/clay-embeddings.md)

## Ingest imagery

- User navigates to `/upload` (Ingest Imagery)
- Drops or selects GeoTIFF tiles; the client checks size (max 100 MB) and type (`.tif/.tiff` among others)
- Tiles upload **directly from the browser to B2** (presigned PUT) under `imagery/`; a progress bar tracks the bytes, then the row switches to "Verifying" while the API HEADs and magic-byte-sniffs the stored object
- On success the tile appears in the Imagery Library and is embeddable by a job
- No imagery to hand? `pnpm run seed` generates synthetic license-clean tiles instead
- See: [Imagery Ingest](features/file-upload.md)

## Browse the Imagery Library

- User navigates to `/library`
- A scoped gallery lists GeoTIFF tiles under `imagery/` (newest first), each card showing a PNG thumbnail and parsed geospatial metadata (dimensions, band count, CRS, GSD)
- A tile whose header can't be parsed (or when the geospatial stack isn't installed) still lists, with a warning instead of metadata
- "Find similar" on a card deep-links to `/search?key=<tile>`
- See: [Imagery Library](features/imagery-library.md), [GeoTIFF Metadata](features/geotiff-metadata.md)

## Search similar scenes

- User navigates to `/search` (or arrives from a Library card with a preselected tile)
- Picks a query tile, a sensor preset, and k, then runs the search
- The API embeds the query with Clay and returns the nearest neighbours from a usearch index built over the embeddings in B2, rendered as a grid with similarity scores
- If no embeddings exist yet, the result explains to run an Embedding Job first
- See: [Similarity Search](features/similarity-search.md)

## Browse and manage all files

- User navigates to `/files` — the never-removable full-bucket explorer over every prefix (`imagery/`, `tiles/`, `embeddings/`, `jobs/`)
- Loads the most recent objects (a full listing measured 2.8s-21s cold; the wait is stated on screen). Tree view with folders, preview, download, delete
- See: [File Browser](features/file-browser.md)

## View the dashboard

- User navigates to `/` (home)
- Stat cards (objects in bucket, storage used, ingested today, downloads), a daily ingest-activity chart, and a Recent Jobs table load from `/files/stats`, `/files/stats/activity`, and `/jobs`
- Empty and error states are explicit — a failed stats fetch never renders "0" as if the bucket were empty
- See: [Dashboard](features/dashboard.md)

## Change preferences

- User navigates to `/settings`
- A banner states the page is mostly a demonstration: only Theme is wired for real; the rest showcases the form patterns this app reuses for the Embedding Job forms
- See: [Settings](features/settings.md)
