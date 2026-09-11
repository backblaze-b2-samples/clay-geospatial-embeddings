<!-- last_verified: 2026-09-11 -->
# Feature: Dashboard

## Purpose
An at-a-glance overview of the geospatial archive on B2 — object/storage stats
and the most recent Clay embedding jobs.

## Used By
- UI: `/` page, `components/dashboard/*`
- API: `GET /files/stats`, `GET /files/stats/activity`, `GET /jobs`

## Core Functions
- `apps/web/src/components/dashboard/stats-cards.tsx` — objects in bucket, storage used, ingested today, downloads
- `apps/web/src/components/dashboard/upload-chart.tsx` — daily ingest activity
- `apps/web/src/components/dashboard/recent-jobs.tsx` — most recent embedding jobs with status
- `apps/web/src/lib/queries.ts` — `useFileStats`, `useUploadActivity`, `useJobs`

## Canonical Files
- Dashboard page: `apps/web/src/app/page.tsx`

## Inputs
- None (reads aggregate stats and job records)

## Outputs
- Rendered stat cards, an activity chart, and a recent-jobs table

## Flow
- Cards and chart read `/files/stats` and `/files/stats/activity` (whole-bucket aggregates via the shared listing cache)
- Recent Jobs reads `/jobs` and links each row to its detail page

## Edge Cases
- Stats fetch fails → inline error (never shows "0" as if the bucket were empty)
- No jobs yet → empty-state prompt to create one

## UX States
- Loading (skeletons + a loading notice) / Error (retry) / Loaded

## Verification
- Test files: `services/api/tests/test_upload_activity.py`, `services/api/tests/test_recent_files.py`, `services/api/tests/test_jobs.py`
- Required cases: stats aggregation, activity windowing, recent jobs listing
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Embedding Jobs](embedding-jobs.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
