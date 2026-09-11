<!-- last_verified: 2026-09-11 -->
# Feature: Imagery Ingest (direct-to-B2 upload)

## Purpose
Ingest GeoTIFF imagery tiles straight into B2 under `imagery/` via a presigned
PUT, so bytes never traverse the API (lifting Vercel's ~4.5 MB Function payload
ceiling). Ingested tiles appear in the Imagery Library and are embeddable by a job.

## Used By
- UI: `/upload` page (`Ingest Imagery`), `components/upload/*`
- API: `POST /upload/presign`, `POST /upload/verify`

## Core Functions
- `services/api/app/service/upload.py` — declared-upload validation, `create_presigned_upload`, `verify_upload`; `UPLOAD_PREFIX = "imagery/"`; `ALLOWED_TYPES` includes `image/tiff`
- `services/api/app/repo/b2_upload.py` — `generate_presigned_upload`, `get_object_head_bytes`
- `services/api/app/runtime/upload.py` — REST handlers
- `apps/web/src/components/upload/*`, `apps/web/src/lib/upload-file-types.ts` (mirrors backend allow-list, includes `.tif/.tiff`)

## Canonical Files
- Upload service: `services/api/app/service/upload.py`

## Inputs
- filename, content_type, size_bytes (declared at presign; size + type are signed into the PUT URL)

## Outputs
- `POST /upload/presign` → `PresignUploadResponse` (presigned PUT under `imagery/`)
- `POST /upload/verify` → `FileUploadResponse` (post-upload HEAD + magic-byte sniff; invalid objects deleted)
- Side effects: object written to B2 `imagery/`; listing cache invalidated

## Flow
- Presign → browser PUTs bytes directly to B2 → verify inspects the stored object
- The signed content-length and content-type mean B2 refuses a mismatched body

## Edge Cases
- Disallowed type / extension mismatch → 415
- Oversized (> `max_file_size`) → 413
- Content bytes don't match the declared type → object deleted, 415
- Key outside `imagery/` at verify → rejected

## UX States
- Dropzone (idle / dragging) / per-file progress / success / error toasts

## Verification
- Test files: `services/api/tests/test_upload_validation.py`, `services/api/tests/test_upload_conflict.py`, `apps/web/src/lib/upload-file-types.test.ts`
- Required cases: presign validation, signature sniff, extension/type checks, prefix enforcement, allow-list parity with the frontend
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Imagery Library](imagery-library.md)
- [File Browser](file-browser.md)
- [App Workflows](../app-workflows.md)
