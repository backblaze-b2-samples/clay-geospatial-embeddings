"use client";

import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import {
  ApiError,
  createJob,
  deleteFile,
  deleteJob,
  getDownloadUrl,
  getFileDetail,
  getFiles,
  getFileStats,
  getHealth,
  getJob,
  getJobs,
  getJobSourcePrefixes,
  getLibrary,
  getPreviewUrl,
  getUploadActivity,
  runJob,
  searchByKey,
  updateJob,
} from "@/lib/api-client";
import type {
  FileMetadata,
  FileMetadataDetail,
  ImageryItem,
  JobCreateRequest,
  JobRecord,
  JobStatus,
  JobUpdateRequest,
  SearchByKeyRequest,
  SearchResponse,
} from "@clay-geospatial-embeddings/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  detail: (key: string) => [...qk.all, "detail", key] as const,
  health: () => [...qk.all, "health"] as const,
  jobs: () => [...qk.all, "jobs"] as const,
  job: (id: string) => [...qk.all, "jobs", id] as const,
  jobSourcePrefixes: () => [...qk.all, "jobs", "source-prefixes"] as const,
  library: (limit?: number) => [...qk.all, "library", limit ?? 100] as const,
};

export type Health = Awaited<ReturnType<typeof getHealth>>;

/**
 * Gate a query on something being open/visible. Deliberately the only option we
 * expose, so callers can't drift the caching policy per call site — the ⌘K
 * palette reuses `useFiles`' key (and therefore its cache) instead of fetching
 * its own private, smaller list.
 */
export interface QueryGate {
  enabled?: boolean;
}

export function useFiles(prefix = "", limit = 100, { enabled = true }: QueryGate = {}) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
    enabled,
  });
}

export function useFileStats({ enabled = true }: QueryGate = {}) {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
    enabled,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

// Rich metadata for an already-stored file. The server recomputes it on demand
// (a full object download), so it's only fetched when `enabled` — i.e. the
// preview dialog is open AND the user expands "Detailed metadata". Kept
// short-lived like the preview URL; cheap correctness under key overwrites.
export function useFileDetail(key: string | undefined, enabled: boolean) {
  return useQuery<FileMetadataDetail, ApiError>({
    queryKey: qk.detail(key ?? ""),
    queryFn: () => getFileDetail(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

// Health poll for the top-of-app B2 banner. `retry: false` and letting a
// failed fetch leave `data` undefined keeps a down API silent (the
// per-component ErrorState covers that); the banner only reacts to an up API
// reporting b2_connected: false. Polls every 60s and on window focus.
export function useHealth() {
  return useQuery<Health>({
    queryKey: qk.health(),
    queryFn: getHealth,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  });
}

/**
 * Drop a deleted object from every cached file list, plus its own cached
 * preview/detail entries.
 *
 * Invalidation alone is not enough: the refetch re-lists the whole bucket and
 * took 5-6s in practice, so the success toast fired while the row was still
 * listed — and using that stale row's Preview 404'd. Editing the cache makes
 * the row disappear with the toast; the invalidation that follows still
 * reconciles against the server.
 *
 * Exported for tests — the mutation below is its only production caller.
 */
export function dropDeletedFileFromCache(qc: QueryClient, fileKey: string) {
  qc.setQueriesData<FileMetadata[]>(
    // Partial key: matches qk.files(prefix, limit) for every prefix/limit.
    { queryKey: [...qk.all, "files"] },
    (previous) =>
      previous ? previous.filter((file) => file.key !== fileKey) : previous,
  );
  // A presigned URL for a deleted key can only 404 now.
  qc.removeQueries({ queryKey: qk.preview(fileKey) });
  qc.removeQueries({ queryKey: qk.detail(fileKey) });
}

/**
 * Fetch a download URL for one file.
 *
 * A mutation, not a query: it has a server side effect (it bumps the download
 * counter) and it must never be cached or replayed. Being a mutation is also
 * what gives the UI an honest pending state — the old code awaited the presign
 * inside a plain click handler, so a slow round trip left the screen completely
 * unchanged and a user could not tell a working download from a dead button.
 *
 * The caller performs the navigation (see `lib/browser-download.ts`) and gets
 * `isPending` / `variables` for the pending row.
 */
export function useDownloadUrl() {
  const qc = useQueryClient();
  return useMutation<{ url: string }, ApiError, FileMetadata>({
    mutationFn: (file) => getDownloadUrl(file.key),
    // The server counted a download, so the dashboard's "Total Downloads" is
    // now stale. Cheap: /files/stats reads a cached bucket listing.
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.stats() }),
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    onSuccess: (_data, fileKey) => {
      // Remove the row immediately, then reconcile everything (lists, stats,
      // activity) against the server in the background.
      dropDeletedFileFromCache(qc, fileKey);
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Embedding Jobs (primary entity) ---------------------------------------

export function useJobs({ enabled = true }: QueryGate = {}) {
  return useQuery<JobRecord[], ApiError>({
    queryKey: qk.jobs(),
    queryFn: getJobs,
    enabled,
  });
}

// How often to re-poll a job that is still working. Short enough that the badge,
// tiles-embedded count, and duration feel live; the run itself finishes in ~25-35s.
const JOB_POLL_INTERVAL_MS = 1500;

/**
 * Polling cadence for a job detail query: poll while the job is still working,
 * stop once it reaches a terminal state. Making this a pure function keeps the
 * "when do we stop polling" rule testable without rendering a component — the
 * `useJob` refetchInterval below is its only production caller.
 */
export function jobPollInterval(status: JobStatus | undefined): number | false {
  return status === "pending" || status === "running" ? JOB_POLL_INTERVAL_MS : false;
}

export function useJob(id: string | undefined, enabled = true) {
  return useQuery<JobRecord, ApiError>({
    queryKey: qk.job(id ?? ""),
    queryFn: () => getJob(id as string),
    enabled: enabled && !!id,
    // Poll while pending/running so a mid-run reload converges to completion on
    // its own and the header badge can't stay stale; stop once terminal.
    refetchInterval: (query) => jobPollInterval(query.state.data?.status),
  });
}

export function useJobSourcePrefixes({ enabled = true }: QueryGate = {}) {
  return useQuery<string[], ApiError>({
    queryKey: qk.jobSourcePrefixes(),
    queryFn: getJobSourcePrefixes,
    enabled,
  });
}

export function useCreateJob() {
  const qc = useQueryClient();
  return useMutation<JobRecord, ApiError, JobCreateRequest>({
    mutationFn: (req) => createJob(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.jobs() }),
  });
}

export function useUpdateJob(id: string) {
  const qc = useQueryClient();
  return useMutation<JobRecord, ApiError, JobUpdateRequest>({
    mutationFn: (req) => updateJob(id, req),
    onSuccess: (job) => {
      qc.setQueryData(qk.job(id), job);
      qc.invalidateQueries({ queryKey: qk.jobs() });
    },
  });
}

export function useDeleteJob() {
  const qc = useQueryClient();
  return useMutation<{ deleted: boolean; id: string }, ApiError, string>({
    mutationFn: (id) => deleteJob(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.jobs() });
      // A deleted job's embeddings are gone, so any list is stale.
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

export function useRunJob(id: string) {
  const qc = useQueryClient();
  return useMutation<JobRecord, ApiError, void>({
    mutationFn: () => runJob(id),
    onSuccess: (job) => {
      qc.setQueryData(qk.job(id), job);
      qc.invalidateQueries({ queryKey: qk.jobs() });
    },
  });
}

// --- Imagery Library --------------------------------------------------------

export function useLibrary(limit = 100, { enabled = true }: QueryGate = {}) {
  return useQuery<ImageryItem[], ApiError>({
    queryKey: qk.library(limit),
    queryFn: () => getLibrary(limit),
    enabled,
  });
}

// --- Similarity search ------------------------------------------------------

export function useSearch() {
  return useMutation<SearchResponse, ApiError, SearchByKeyRequest>({
    mutationFn: (req) => searchByKey(req),
  });
}
