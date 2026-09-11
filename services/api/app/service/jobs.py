"""Embedding Job lifecycle — create, read, edit, delete, and run.

Run streams each imagery tile from B2, reads its pixels (rasterio), embeds it
with Clay (on the autodetected device), and writes the ``.npy`` embedding back
to B2. Native-ML failures are contained: a missing/failed engine marks the job
``failed`` with an actionable message and the API process stays alive.
"""

import logging
import time
import uuid
from datetime import UTC, datetime

from app.config import settings
from app.config.prefixes import EMBEDDINGS_PREFIX, IMAGERY_PREFIX
from app.repo import (
    delete_job as _delete_job_record,
)
from app.repo import (
    delete_prefix,
    embedding_key,
    get_object_bytes,
    list_keys,
    load_job,
    save_embedding,
    save_job,
)
from app.repo import (
    list_jobs as _list_job_records,
)
from app.service import clay
from app.service.clay import EngineUnavailableError
from app.service.geotiff import GeoTiffError, read_pixels
from app.types import (
    EmbeddingRef,
    JobConfig,
    JobCreateRequest,
    JobRecord,
    JobUpdateRequest,
)

logger = logging.getLogger(__name__)

_TIFF_SUFFIXES = (".tif", ".tiff")


class JobNotFoundError(Exception):
    def __init__(self, detail: str = "Job not found"):
        self.detail = detail
        super().__init__(detail)


class JobConflictError(Exception):
    def __init__(self, detail: str = "Job is running"):
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def _to_record(data: dict) -> JobRecord:
    return JobRecord.model_validate(data)


def create_job(req: JobCreateRequest) -> JobRecord:
    now = _now()
    record = JobRecord(
        id=uuid.uuid4().hex[:12],
        name=req.name.strip(),
        status="pending",
        config=req.config,
        created_at=now,
        updated_at=now,
    )
    save_job(record.id, record.model_dump(mode="json"))
    return record


def get_job(job_id: str) -> JobRecord:
    data = load_job(job_id)
    if data is None:
        raise JobNotFoundError()
    return _to_record(data)


def list_jobs() -> list[JobRecord]:
    records = [_to_record(d) for d in _list_job_records()]
    records.sort(key=lambda r: r.created_at, reverse=True)
    return records


def update_job(job_id: str, req: JobUpdateRequest) -> JobRecord:
    record = get_job(job_id)
    if record.status == "running":
        raise JobConflictError("Cannot edit a job while it is running")
    if req.name is not None:
        record.name = req.name.strip()
    if req.config is not None:
        record.config = req.config
    record.updated_at = _now()
    save_job(record.id, record.model_dump(mode="json"))
    return record


def delete_job(job_id: str) -> None:
    """Delete the job record and its own embeddings only (scoped)."""
    record = get_job(job_id)
    if record.status == "running":
        raise JobConflictError("Cannot delete a job while it is running")
    # Scoped: only this job's embedding prefix, never the shared bucket.
    delete_prefix(f"{EMBEDDINGS_PREFIX}{job_id}/")
    _delete_job_record(job_id)


def embedding_tile_map() -> dict[str, str]:
    """Map every stored embedding key -> its source tile key (across all jobs).

    Used by similarity search so a hit can name the imagery tile it came from.
    """
    mapping: dict[str, str] = {}
    for record in list_jobs():
        for emb in record.embeddings:
            mapping[emb.embedding_key] = emb.tile_key
    return mapping


def list_source_prefixes() -> list[str]:
    """Distinct sub-prefixes under ``imagery/`` for the create-form selector."""
    prefixes = {IMAGERY_PREFIX}
    for key in list_keys(IMAGERY_PREFIX):
        rest = key[len(IMAGERY_PREFIX) :]
        if "/" in rest:
            prefixes.add(IMAGERY_PREFIX + rest.split("/", 1)[0] + "/")
    return sorted(prefixes)


def _list_tiles(source_prefix: str) -> list[str]:
    return [k for k in list_keys(source_prefix) if k.lower().endswith(_TIFF_SUFFIXES)]


def _finish(record: JobRecord, *, status: str, message: str, started: float) -> JobRecord:
    record.status = status  # type: ignore[assignment]
    record.message = message
    record.finished_at = _now()
    record.updated_at = record.finished_at
    record.duration_seconds = round(time.monotonic() - started, 2)
    save_job(record.id, record.model_dump(mode="json"))
    return record


def run_job(job_id: str) -> JobRecord:
    """Run the embedding pipeline. Returns the final record; never 500s on ML failure."""
    record = get_job(job_id)
    if record.status == "running":
        raise JobConflictError("Job is already running")

    started = time.monotonic()
    record.status = "running"
    record.started_at = _now()
    record.updated_at = record.started_at
    record.message = "Running"
    record.embeddings = []
    record.tiles_embedded = 0
    save_job(record.id, record.model_dump(mode="json"))

    config: JobConfig = record.config
    preset = clay.get_preset(config.sensor)
    tiles = _list_tiles(config.source_prefix)
    record.tiles_total = len(tiles)

    if not tiles:
        return _finish(
            record,
            status="failed",
            message=f"No .tif/.tiff tiles found under '{config.source_prefix}'. "
            "Seed imagery first (scripts/seed_imagery.py) or upload GeoTIFFs.",
            started=started,
        )

    # Resolve device up front so a missing engine fails fast and cleanly.
    try:
        device = clay.select_device(settings.clay_device)
    except EngineUnavailableError as e:
        return _finish(record, status="failed", message=str(e), started=started)
    record.device = device

    embeddings: list[EmbeddingRef] = []
    errors: list[str] = []
    for tile_key in tiles:
        try:
            data = get_object_bytes(tile_key)
            pixels = read_pixels(data, preset.band_count)
        except (GeoTiffError, RuntimeError) as e:
            errors.append(f"{tile_key}: {e}")
            continue
        try:
            vector = clay.embed_pixels(pixels, preset, device)
        except EngineUnavailableError as e:
            # Device fallback: unsupported MPS/CUDA op -> retry once on CPU.
            if device != "cpu":
                logger.warning("Embed failed on %s (%s); falling back to CPU", device, e)
                device = "cpu"
                record.device = "cpu"
                clay.reset_model_cache()
                try:
                    vector = clay.embed_pixels(pixels, preset, "cpu")
                except EngineUnavailableError as e2:
                    return _finish(record, status="failed", message=str(e2), started=started)
            else:
                return _finish(record, status="failed", message=str(e), started=started)
        emb_key = embedding_key(job_id, tile_key)
        save_embedding(emb_key, vector)
        embeddings.append(
            EmbeddingRef(tile_key=tile_key, embedding_key=emb_key, dims=len(vector))
        )
        record.tiles_embedded = len(embeddings)

    record.embeddings = embeddings
    if not embeddings:
        return _finish(
            record,
            status="failed",
            message="No tiles could be embedded. " + "; ".join(errors[:3]),
            started=started,
        )
    msg = f"Embedded {len(embeddings)}/{len(tiles)} tiles on {record.device}."
    if errors:
        msg += f" {len(errors)} skipped."
    return _finish(record, status="succeeded", message=msg, started=started)
