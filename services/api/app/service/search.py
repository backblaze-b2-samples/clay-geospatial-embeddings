"""Similarity search — k-NN scene retrieval over Clay embeddings in B2.

Embeds a query tile with Clay (on the autodetected device), builds a usearch
index over every embedding under ``embeddings/`` (loaded from B2), and returns
the nearest neighbours. Native-ML failures surface as SearchUnavailableError so
the route answers 503 with an actionable message rather than 500ing.
"""

from app.config import settings
from app.repo import build_index, get_object_bytes, list_embedding_keys
from app.service import clay
from app.service.clay import EngineUnavailableError
from app.service.geotiff import GeoTiffError, read_pixels
from app.service.jobs import embedding_tile_map
from app.types import SearchByKeyRequest, SearchHit, SearchResponse


class SearchUnavailableError(Exception):
    """Raised when the ML stack is missing or no embeddings exist yet."""

    def __init__(self, detail: str, status_code: int = 503):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


def _embed_query(req: SearchByKeyRequest):
    preset = clay.get_preset(req.sensor)
    try:
        device = clay.select_device(settings.clay_device)
    except EngineUnavailableError as e:
        raise SearchUnavailableError(str(e)) from e
    try:
        data = get_object_bytes(req.query_key)
        pixels = read_pixels(data, preset.band_count)
    except (RuntimeError, GeoTiffError) as e:
        raise SearchUnavailableError(f"Could not read query tile: {e}", 400) from e
    try:
        return clay.embed_pixels(pixels, preset, device)
    except EngineUnavailableError as e:
        if device != "cpu":
            clay.reset_model_cache()
            try:
                return clay.embed_pixels(pixels, preset, "cpu")
            except EngineUnavailableError as e2:
                raise SearchUnavailableError(str(e2)) from e2
        raise SearchUnavailableError(str(e)) from e


def search_by_key(req: SearchByKeyRequest) -> SearchResponse:
    """Return up to ``k`` scenes most similar to the query tile."""
    if not list_embedding_keys():
        raise SearchUnavailableError(
            "No embeddings in the archive yet — run an Embedding Job first.", 409
        )
    query_vector = _embed_query(req)
    index = build_index(embedding_tile_map())
    hits = [
        SearchHit(tile_key=tile_key, embedding_key=emb_key, score=round(score, 4))
        for emb_key, tile_key, score in index.query(query_vector, req.k)
    ]
    return SearchResponse(query_key=req.query_key, index_size=index.size, hits=hits)
