<!-- last_verified: 2026-09-11 -->
# Feature: Embedding Jobs (primary entity)

## Purpose
Create, view, edit, delete, and run named jobs that embed a set of B2 imagery
tiles with the Clay foundation model. Job records persist as JSON in B2 — no
database.

## Used By
- UI: `/jobs` (list + create form), `/jobs/[id]` (detail with run / edit / delete)
- API: `GET /jobs`, `POST /jobs`, `GET /jobs/source-prefixes`, `GET /jobs/{job_id}`, `PATCH /jobs/{job_id}`, `DELETE /jobs/{job_id}`, `POST /jobs/{job_id}/run`

## Core Functions
- `services/api/app/service/jobs.py` — lifecycle: `create_job`, `get_job`, `list_jobs`, `update_job`, `delete_job`, `run_job`, `list_source_prefixes`, `embedding_tile_map`
- `services/api/app/repo/job_store.py` — persists `jobs/<id>.json` in B2
- `services/api/app/repo/embeddings.py` — writes `embeddings/<job_id>/<hash>.npy`
- `services/api/app/runtime/jobs.py` — REST handlers
- `apps/web/src/components/jobs/job-form.tsx` — create/edit form (selectors + create hints)
- `apps/web/src/components/jobs/job-table.tsx`, `job-detail.tsx`, `status-badge.tsx`
- `apps/web/src/lib/queries.ts` — `useJobs`, `useJob`, `useCreateJob`, `useUpdateJob`, `useDeleteJob`, `useRunJob`

## Canonical Files
- Lifecycle service: `services/api/app/service/jobs.py`
- Form exemplar this follows: `apps/web/src/components/settings/settings-form.tsx`

## Inputs
- name: string (free text)
- config: { source_prefix, tile_size (256|512), model (clay-v1.5), sensor }

## Outputs
- `JobRecord` JSON at `jobs/<id>.json`; embeddings `.npy` under `embeddings/<id>/`
- Side effects: B2 writes; a run reads imagery, runs Clay, writes embeddings

## Flow
- Create → status `pending`, record written to B2
- Run → status `running`; list tiles under `source_prefix`, read pixels, embed each with Clay on the autodetected device, write `.npy`, then status `succeeded`/`failed`
- Edit → allowed only while not running (rename / reconfigure)
- Delete → removes `jobs/<id>.json` and only `embeddings/<id>/` (scoped; imagery untouched)

## Edge Cases
- No tiles under the prefix → run marked `failed` with a seed/upload hint
- Clay stack not installed → run marked `failed` with the install command (no 500)
- Edit/delete a running job → 409 Conflict
- Missing job → 404

## UX States
- Empty: "No embedding jobs yet" with a create prompt
- Running: in-progress alert; Run/Edit/Delete disabled. The detail query polls (`useJob` `refetchInterval`, ~1.5s) while the job is `pending`/`running` and stops once terminal, so the badge and duration update live and a mid-run reload converges to completion on its own. `run_job` persists the record only at start (`tiles_embedded` = 0) and end, not per tile, so the tiles-embedded count jumps from 0 to its final value when the run finishes rather than counting up. The header badge derives from the live/polled status (shows "Running" while a run is in flight), so it can't contradict the button/alert.
- Error/failed: the failure message is surfaced on the detail page
- Succeeded (embeddings exist): the Embeddings card header offers a "Find similar scenes" action linking to `/search?key=<tile>` (pre-selects one of this job's tiles), chaining the goal's final stage

## Verification
- Test files: `services/api/tests/test_jobs.py`
- Required cases: create/read/update/delete, missing job 404, run with no tiles fails, run without engine fails gracefully
- Focused verify command: `pnpm test:api`
- Default pre-PR verify command: `pnpm verify`
- Full local verify command: `pnpm verify:full` when E2E/live prerequisites apply
- Pass criteria: focused tests and `pnpm verify` green

## Related Docs
- [Clay Embeddings](clay-embeddings.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md)
- [App Workflows](../app-workflows.md)
