export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  /** Set when a format-specific extractor was skipped or failed (e.g. an image
   *  above the decompression-bomb decode limit). Core fields stay exact. */
  metadata_warning: string | null;
  // Image-specific
  image_width: number | null;
  image_height: number | null;
  exif: Record<string, string> | null;
  // PDF-specific
  pdf_pages: number | null;
  pdf_author: string | null;
  pdf_title: string | null;
  // Audio/Video
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

/** A short-lived presigned PUT the browser uploads a file directly to B2 with.
 *  `headers` are signed into the URL, so the browser must send them verbatim. */
export interface PresignUploadResponse {
  key: string;
  url: string;
  method: string;
  content_type: string;
  headers: Record<string, string>;
  expires_in: number;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Embedding Jobs (primary entity) ---------------------------------------

export type TileSize = 256 | 512;
export type ModelName = "clay-v1.5";
export type SensorPreset = "sentinel-2-rgb" | "sentinel-2-l2a" | "naip-rgb";
export type JobStatus = "pending" | "running" | "succeeded" | "failed";

export interface JobConfig {
  source_prefix: string;
  tile_size: TileSize;
  model: ModelName;
  sensor: SensorPreset;
}

export interface EmbeddingRef {
  tile_key: string;
  embedding_key: string;
  dims: number;
}

export interface JobRecord {
  id: string;
  name: string;
  status: JobStatus;
  config: JobConfig;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  finished_at: string | null;
  device: string | null;
  message: string | null;
  tiles_total: number;
  tiles_embedded: number;
  duration_seconds: number | null;
  embeddings: EmbeddingRef[];
}

export interface JobCreateRequest {
  name: string;
  config: JobConfig;
}

export interface JobUpdateRequest {
  name?: string;
  config?: JobConfig;
}

// --- Imagery Library --------------------------------------------------------

export interface GeoTiffMetadata {
  width: number | null;
  height: number | null;
  band_count: number | null;
  crs: string | null;
  bounds: number[] | null;
  gsd: number | null;
  dtype: string | null;
}

export interface ImageryItem {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  uploaded_at: string;
  metadata: GeoTiffMetadata | null;
  metadata_warning: string | null;
}

// --- Similarity search ------------------------------------------------------

export interface SearchByKeyRequest {
  query_key: string;
  k: number;
  sensor: SensorPreset;
}

export interface SearchHit {
  tile_key: string;
  embedding_key: string;
  score: number;
}

export interface SearchResponse {
  query_key: string;
  index_size: number;
  hits: SearchHit[];
}
