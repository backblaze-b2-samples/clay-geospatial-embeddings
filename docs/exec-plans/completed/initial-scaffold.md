# Build plan — `clay-geospatial-embeddings`

Source of truth for the starter tree:
`.claude/scratch/vcsk-b18cca71-c4dc-411d-b307-c55536bfbff3/` (fetched fresh in Phase 0).
Delta below is computed against that tree. The starter kit is the ceiling —
strip what this app doesn't need rather than rebuild.

---

## 1. Purpose

`clay-geospatial-embeddings` is a B2 sample for geospatial AI teams (climate-tech,
agricultural analytics, government remote-sensing) that need rich semantic
embeddings over large satellite/aerial imagery archives for change detection,
land-cover classification, and scene retrieval. It runs the **Clay foundation
model locally** (https://github.com/Clay-foundation/model) against GeoTIFF imagery
tiles stored in Backblaze B2 and writes geospatial embedding tensors back to B2 —
making B2 the storage backbone for the whole pipeline: raw imagery (`imagery/`),
normalized tiles (`tiles/`), embedding artifacts (`embeddings/`), and job records
(`jobs/`). A lightweight vector index over the embeddings powers similarity search
("find scenes like this one") across the archive. Runs on local OSS — **no second
API key, B2 credentials only.**

---

## 2. Architecture delta from vibe-coding-starter-kit

The starter is a Next.js (`apps/web`) + FastAPI (`services/api`) pnpm monorepo with
a B2 S3 repo layer, a full-bucket file browser, direct-to-B2 presigned upload, a
dashboard, a settings page, and a design-system page. We keep the shell and the B2
plumbing, repurpose upload + dashboard + metadata for geospatial, and add the Clay
embedding pipeline, an imagery library, and similarity search.

### KEEP (as-is or lightly adapted)
- Monorepo layout: `apps/web`, `services/api`, `packages/shared`, `infra/`, `scripts/`.
- **B2 S3 repo layer** `services/api/app/repo/b2_client.py` + `b2_object.py` +
  `b2_upload.py` + `list_cache.py` + `counter.py` — S3-compatible, custom
  user-agent, presigned URLs, single-flight listing cache. (Env-var + user-agent
  remap under §3.)
- **Full-bucket explorer** `apps/web/src/components/files/file-browser.tsx` +
  `app/files/page.tsx` + file preview/metadata panel. **MANDATORY keep — never
  removable.** It browses the whole bucket (`imagery/`, `tiles/`, `embeddings/`,
  `jobs/`).
- Direct-to-B2 presigned **upload** (`components/upload/*`, `runtime/upload.py`,
  `service/upload.py`) — repurposed to ingest GeoTIFF tiles into `imagery/`.
- **Dashboard** shell (`components/dashboard/*`) — repurposed to archive/job stats.
- **Settings** page + `components/settings/settings-form.tsx` — kept; it is the
  in-repo exemplar for form UX (selectors + create-form default hints), reused by
  the new Embedding Job forms.
- Design-system page (`app/design/*`, `components/design/*`) and the whole shadcn
  `components/ui/*` primitive set (Select, RadioGroup, Form, Dialog, Table, etc.).
- Layout chrome: sidebar, header, command palette, health banner, theme provider.
- Runtime: `config/settings.py`, `runtime/health.py`, `runtime/metrics.py`,
  `runtime/ratelimit.py`, error/types modules, test harness, CI, `AGENTS.md`.

### TRIM (remove from starter)
- Generic **metadata-extraction** feature as-is
  (`service/metadata.py` generic MIME/EXIF logic, `docs/features/metadata-extraction.md`,
  `types` tied only to generic extraction) — **repurpose** into GeoTIFF metadata
  (CRS, bounds, band count, GSD/resolution) read with `rasterio` for the Imagery
  Library, rather than deleting the concept. Delete the generic doc; add
  `geotiff-metadata` doc.
- Any starter demo copy / PRODUCT.md framing about "vibe coding" / generic uploads —
  rewrite for the geospatial narrative.
- `railway.json` / Railway infra references may stay but must be renamed; drop
  starter-only marketing text in README.

### ADD (new for clay-geospatial-embeddings)
- **Clay embedding engine** `services/api/app/service/clay/` — loads Clay's own
  model (device autodetect CUDA→MPS→CPU, CPU default), builds the Clay datacube
  from a tile + sensor preset, produces the embedding vector. (§4 feature 2.)
- **Embedding Jobs** primary entity: `service/jobs.py`, `runtime/jobs.py`,
  `repo/job_store.py` (JSON job records persisted in B2 under `jobs/`), full
  CRUD+run REST surface; web pages `app/jobs/` (list + `[id]` detail) and
  `components/jobs/*` (job table, create/edit form, run/status).
- **Imagery Library** (sample-specific scoped asset explorer): `app/library/` +
  `components/library/*` — gallery of GeoTIFF tiles scoped to `imagery/` with PNG
  thumbnails + GeoTIFF metadata. **This is the mandatory sample-scoped explorer,
  distinct from the never-removable full-bucket explorer.**
- **Similarity search** (Serve/Query): `service/search.py` + `repo/vector_index.py`
  (usearch index built over embedding tiles loaded from B2) + `app/search/` +
  `components/search/*` — pick/upload a query tile → embed → k-NN over the archive.
- **Seed script** `scripts/seed_imagery.py` — generates a small set (~8) of
  synthetic multispectral GeoTIFF tiles (rasterio + numpy) into `imagery/` so the
  full pipeline is reproducible from a fresh clone with no multi-TB download and no
  licensing concerns.
- `docs/exec-plans/completed/initial-scaffold.md` (this plan, moved on PASS).

---

## 3. B2 surface (S3-compatible only — no b2-native)

All access via the S3-compatible API through the kept `boto3` client
(`get_s3_client`). No b2-native (`b2sdk`) usage anywhere.

| Operation | Where | Purpose |
|---|---|---|
| `put_object` | upload, tile cache, embedding write, job record write | imagery→`imagery/`, normalized→`tiles/`, `.npy`→`embeddings/<job_id>/`, job JSON→`jobs/<id>.json` |
| `get_object` | embed pipeline, search, preview | stream GeoTIFF tiles, load `.npy` embeddings |
| `list_objects_v2` | explorer, library, dashboard, index build | browse prefixes, aggregate stats, enumerate embeddings |
| `head_object` | metadata panel, job read | object metadata |
| `delete_object` | job delete, danger zone | scoped delete of a job's own `embeddings/<job_id>/` + `jobs/<id>.json` |
| `generate_presigned_url` (GET + PUT) | download/preview + direct upload | kept from starter |

**B2 standards to enforce via `/b2-doctor` (the starter is NOT fully compliant —
these are required transforms, not optional):**
1. **S3 default** — already S3 via boto3. Keep; no b2-native added.
2. **Custom user-agent** — `config=Config(user_agent_extra=...)` exists but the
   value is the starter's `"b2ai-oss-start"`. Change to **`clay-geospatial-embeddings`**.
3. **Standardized `B2_*` env names** — the starter uses non-standard names. Remap:
   - `B2_KEY_ID` → **`B2_APPLICATION_KEY_ID`**
   - keep **`B2_APPLICATION_KEY`**, **`B2_BUCKET_NAME`**
   - `B2_ENDPOINT` → derive from **`B2_REGION`** (settings computes
     `https://s3.{B2_REGION}.backblazeb2.com`); add `B2_REGION` (e.g. `us-west-004`)
   - `B2_PUBLIC_URL` → **`B2_PUBLIC_URL_BASE`**
   Update `config/settings.py` fields, `.env.example`, `setup_b2_cors.py`,
   connectivity live test, README, and any doc referencing the old names.

---

## 4. Key features (seed README + `docs/features/<feature>.md` stubs)

> No feature uses a non-B2 **external** API — Clay is on-device. Per
> `api-provider-selection.md` step 2 rule 1 (the sample's whole point is a local
> capability), LOCAL is the default; there is **no external provider and no second
> key**. The only "provider" field that matters is the local-ML device rule.

1. **Embedding Jobs** *(primary entity — full lifecycle)* — create, view, edit,
   delete, and run named jobs that embed a set of B2 imagery tiles with Clay.
   `deployment: local` (drives Clay). Job records persist as JSON in B2 (`jobs/`).
2. **Local Clay foundation-model embedding** — Clay's **own** model runs on-device
   to turn imagery tiles into geospatial embedding vectors written to `embeddings/`.
   `deployment: local`; provider = Clay (OSS, no key); est. cost per full demo run
   = **$0** (local compute only); key env var = **none**. **Device rule (hard):**
   auto-detect **CUDA → Apple MPS → CPU**, **default CPU**. Clay/PyTorch MPS
   coverage is partial — attempt MPS, fall back to CPU on any unsupported-op error;
   CPU is the safe default. Optional `CLAY_DEVICE` override (`auto|cpu|cuda|mps`).
3. **Imagery Library** — scoped asset explorer over `imagery/`: GeoTIFF gallery
   with PNG thumbnails and geospatial metadata (CRS, bounds, bands, GSD).
   `deployment: local` (rasterio read).
4. **Similarity search over embeddings** — usearch vector index built over the
   `.npy` embedding tiles loaded from B2; pick/upload a tile → embed → k-NN scene
   retrieval. `deployment: local`.
5. **Full-bucket explorer** — kept from starter; browses every prefix. (Never removable.)
6. **B2 storage backbone** — imagery, normalized tiles, embeddings, and job records
   all in one B2 bucket via the S3 API with custom user-agent and standard `B2_*` vars.

### Local-ML build notes (headline capability — must use Clay's own engine)
- **Use Clay's actual model, never a substitute** (repo rule: a vendor-themed
  sample uses that vendor's own engine for the headline capability). Install
  `claymodel` from PyPI if it resolves cleanly; otherwise
  `pip install "git+https://github.com/Clay-foundation/model"`. Load the Clay v1.5
  checkpoint (HuggingFace `made-with-clay/Clay`; public — `HF_TOKEN` optional, not
  required). Pin versions in `requirements.txt` / `requirements.lock`.
- Build the Clay datacube per tile: `pixels` (B,C,H,W), band-center `waves`
  (from the sensor preset), `gsd`, `time` (week/hour), `latlon`. For synthetic
  seed tiles use nominal latlon/time and the preset's wavelengths.
- **Contain native-ML crashes in-repo** (expected on macOS): guard model load and
  inference; on failure mark the job `failed` with a clear message and keep the API
  process alive — surface a crash only if it BLOCKS the whole run.
- Keep the seed set tiny (~8 tiles, 256×256) so a full CPU demo run completes in a
  reasonable time. Cache normalized tiles to `tiles/` to avoid reprocessing.
- Heavy deps confirmed to have arm64 wheels: `torch`, `rasterio`, `numpy`,
  `usearch`, `pillow`. Clay's package is the main install risk — contain and fix
  in-repo; do NOT swap in a different model to dodge it.

### Primary-entity lifecycle — Embedding Job (ALL verbs built; `omitted_ui_verbs: []`)
| Verb | UI | REST | Notes |
|---|---|---|---|
| **create** | `/jobs` "New job" form | `POST /jobs` | writes `jobs/<id>.json`, status `pending` |
| **read** | `/jobs` list + `/jobs/[id]` detail | `GET /jobs`, `GET /jobs/{id}` | config, status, embedding outputs, timing |
| **edit** | detail "Edit" form | `PATCH /jobs/{id}` | rename / reconfigure while not running |
| **delete** | detail + list row action | `DELETE /jobs/{id}` | scoped delete of `embeddings/<id>/` + `jobs/<id>.json` only |
| **run** | detail "Run" button | `POST /jobs/{id}/run` | stream tiles→normalize→Clay embed→write `.npy`→rebuild index |

Every verb is user-accessible and built. No verb is omitted; `omitted_ui_verbs`
in `build-result.json` is `[]`.

### Form UX conventions (Embedding Job create/edit)
Follow the exemplar `apps/web/src/components/settings/settings-form.tsx`.
- **Selectors for finite-value fields (create + edit):**
  - Tile size → `RadioGroup`/segmented: **256** / **512**.
  - Model → `Select`: **Clay v1.5** (single current option, still a Select).
  - Sensor / band preset → `Select`: **Sentinel-2 RGB** / **Sentinel-2 L2A (multispectral)** / **NAIP RGB**.
  - Source prefix → `Select` populated from discovered `imagery/` sub-prefixes, with a free-text fallback.
  - Job name → free text (the only free-text field).
- **Create-form default hints** (placeholder / `FormDescription` guidance only —
  never an autofill button): name `e.g. sentinel2-tirana-2024`; source
  `imagery/`; tile size `256`; model `Clay v1.5`; sensor `Sentinel-2 RGB`. These
  defaults give a sound first test run. The edit form opens pre-filled from the
  real job record (no default hints).

---

## 5. Doc transforms
- **Rewrite:** `README.md`, `ARCHITECTURE.md`, `PRODUCT.md`, `docs/app-workflows.md`
  for the Clay/geospatial narrative and the new page set.
- **Feature docs — rewrite/adapt:** `docs/features/file-browser.md` (keep as
  full-bucket explorer), `docs/features/file-upload.md` → imagery ingest,
  `docs/features/dashboard.md` → geospatial archive dashboard,
  `docs/features/settings.md` (keep).
- **Feature docs — delete:** `docs/features/metadata-extraction.md` (generic).
- **Feature docs — add stubs** (from `_template.md`): `embedding-jobs.md`,
  `clay-embeddings.md`, `imagery-library.md`, `similarity-search.md`,
  `geotiff-metadata.md`.

---

## 6. Rename table (`vibe-coding-starter-kit` → `clay-geospatial-embeddings`)
| From | To | Where |
|---|---|---|
| `vibe-coding-starter-kit` (kebab) | `clay-geospatial-embeddings` | root `package.json` name, README, docs, UTM `utm_content` |
| `@vibe-coding-starter-kit/web` | `@clay-geospatial-embeddings/web` | pnpm workspace scope, all `--filter` scripts, `apps/web/package.json` |
| `Vibe Coding Starter Kit` (Title) | `Clay Geospatial Embeddings` | README H1, `app/layout.tsx` metadata, header/sidebar branding, PRODUCT.md |
| `vibe_coding_starter_kit` (snake) | `clay_geospatial_embeddings` | any Python identifiers/paths (if present) |
| `b2ai-oss-start` (user-agent) | `clay-geospatial-embeddings` | `repo/b2_client.py` `user_agent_extra` |
| `B2_KEY_ID` / `B2_ENDPOINT` / `B2_PUBLIC_URL` | `B2_APPLICATION_KEY_ID` / `B2_REGION` (+derived endpoint) / `B2_PUBLIC_URL_BASE` | `config/settings.py`, `.env.example`, scripts, docs |
| starter service/image/workflow slugs | `clay-geospatial-embeddings` | `railway.json`, `vercel.json`, `.github/workflows/*`, image tags |

---

## Notes / open tensions
- **Full-bucket explorer kept despite the app being job-centric** — required by the
  skill (never removable). It coexists with the scoped Imagery Library; the two
  serve different needs (whole-bucket audit vs. curated imagery gallery).
- **No DB / no second service** — job records live as JSON in B2 (`jobs/`) to keep
  "B2 credentials only" true and avoid a second dependency.
- **Synthetic seed imagery** keeps the demo reproducible and license-clean;
  real archives (tens–hundreds of TB) are described in docs as the production case.
- **Clay install is the main build risk** — contain in-repo; never substitute the model.
