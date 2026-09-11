"""Similarity-search models — k-NN scene retrieval over embeddings."""

from pydantic import BaseModel, Field

from app.types.jobs import SensorPreset


class SearchByKeyRequest(BaseModel):
    """Search for scenes similar to an existing imagery tile in B2."""

    query_key: str
    k: int = Field(default=6, ge=1, le=50)
    sensor: SensorPreset = "sentinel-2-rgb"


class SearchHit(BaseModel):
    tile_key: str
    embedding_key: str
    # Cosine similarity in [0, 1]; higher is more similar.
    score: float


class SearchResponse(BaseModel):
    query_key: str
    index_size: int
    hits: list[SearchHit] = Field(default_factory=list)
