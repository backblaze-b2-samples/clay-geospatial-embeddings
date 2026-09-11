"""Embedding Job models — the app's primary entity.

A job describes a set of B2 imagery tiles to embed with the Clay foundation
model and records the outcome. Job records persist as JSON in B2 under
``jobs/<id>.json`` (no database — B2 credentials only).
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Finite-value fields are Literals so both the API boundary and the frontend
# selectors share one closed set (Form UX: selectors, not free text).
TileSize = Literal[256, 512]
ModelName = Literal["clay-v1.5"]
SensorPreset = Literal["sentinel-2-rgb", "sentinel-2-l2a", "naip-rgb"]
JobStatus = Literal["pending", "running", "succeeded", "failed"]


class JobConfig(BaseModel):
    """Everything needed to reproduce an embedding run."""

    source_prefix: str = "imagery/"
    tile_size: TileSize = 256
    model: ModelName = "clay-v1.5"
    sensor: SensorPreset = "sentinel-2-rgb"


class EmbeddingRef(BaseModel):
    """One embedding artifact produced by a run."""

    tile_key: str
    embedding_key: str
    dims: int


class JobRecord(BaseModel):
    """A full job record as persisted in B2."""

    id: str
    name: str
    status: JobStatus = "pending"
    config: JobConfig = Field(default_factory=JobConfig)
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    # Resolved compute device for the last run (cpu/cuda/mps).
    device: str | None = None
    # Human-readable status/error message (e.g. why a run failed).
    message: str | None = None
    tiles_total: int = 0
    tiles_embedded: int = 0
    duration_seconds: float | None = None
    embeddings: list[EmbeddingRef] = Field(default_factory=list)


class JobCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    config: JobConfig = Field(default_factory=JobConfig)


class JobUpdateRequest(BaseModel):
    """Rename / reconfigure a job while it is not running.

    All fields optional — a PATCH updates only what it carries.
    """

    name: str | None = Field(default=None, min_length=1, max_length=120)
    config: JobConfig | None = None
