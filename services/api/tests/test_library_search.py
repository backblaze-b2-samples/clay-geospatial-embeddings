"""Imagery Library, similarity search, and Clay engine degradation tests.

Hermetic: B2 and the ML stack are mocked / absent. These assert the graceful
paths (metadata warning when rasterio is absent, actionable errors when there
are no embeddings or no engine), which is what the base test venv can prove.
"""

from datetime import UTC, datetime

import pytest

from app.service import library as library_svc
from app.service import search as search_svc
from app.service.clay import EngineUnavailableError, get_preset, select_device
from app.types import FileMetadata, SearchByKeyRequest


def _file(key: str) -> FileMetadata:
    return FileMetadata(
        key=key,
        filename=key.rsplit("/", 1)[-1],
        folder="imagery/",
        size_bytes=128,
        size_human="128 B",
        content_type="image/tiff",
        uploaded_at=datetime.now(UTC),
    )


def test_list_imagery_scopes_to_tiles(monkeypatch):
    files = [_file("imagery/a.tif"), _file("imagery/readme.txt"), _file("imagery/b.tiff")]
    monkeypatch.setattr(library_svc, "list_files", lambda prefix="": files)
    monkeypatch.setattr(library_svc, "get_object_bytes", lambda key: b"data")
    items = library_svc.list_imagery()
    keys = {i.key for i in items}
    assert keys == {"imagery/a.tif", "imagery/b.tiff"}  # non-tiff excluded
    # Without rasterio installed, metadata is None but the item still lists.
    for item in items:
        assert item.metadata is not None or item.metadata_warning is not None


def test_search_without_embeddings_is_actionable(monkeypatch):
    monkeypatch.setattr(search_svc, "list_embedding_keys", lambda *a, **k: [])
    with pytest.raises(search_svc.SearchUnavailableError) as excinfo:
        search_svc.search_by_key(SearchByKeyRequest(query_key="imagery/a.tif"))
    assert excinfo.value.status_code == 409


class _FakeIndex:
    """Stands in for a built usearch index: returns a pre-ranked hit list."""

    def __init__(self, ranked: list[tuple[str, str, float]]):
        self._ranked = ranked

    @property
    def size(self) -> int:
        return len(self._ranked)

    def query(self, vector, k):
        return self._ranked[:k]


def test_search_excludes_query_tile_and_dedups_by_tile_key(monkeypatch):
    """Ranking must drop the query tile itself and keep one hit per source tile.

    Every job re-embeds the same imagery into the shared archive, so the raw
    ranked list is dominated by copies of the query tile and duplicate tiles.
    """
    query_tile = "imagery/a.tif"
    ranked = [
        ("embeddings/j1/a.npy", "imagery/a.tif", 1.0),  # self — must be excluded
        ("embeddings/j2/a.npy", "imagery/a.tif", 0.99),  # self copy — excluded
        ("embeddings/j1/b.npy", "imagery/b.tif", 0.90),  # other — best copy of b
        ("embeddings/j2/b.npy", "imagery/b.tif", 0.85),  # other — dup of b, drop
        ("embeddings/j1/c.npy", "imagery/c.tif", 0.80),  # other — distinct scene
    ]
    monkeypatch.setattr(search_svc, "list_embedding_keys", lambda *a, **k: ["x"])
    monkeypatch.setattr(search_svc, "embedding_tile_map", lambda: {})
    monkeypatch.setattr(search_svc, "_embed_query", lambda req: [0.0])
    monkeypatch.setattr(search_svc, "build_index", lambda *a, **k: _FakeIndex(ranked))

    resp = search_svc.search_by_key(SearchByKeyRequest(query_key=query_tile, k=6))

    # Never returns the query tile itself...
    assert all(hit.tile_key != query_tile for hit in resp.hits)
    # ...and returns at most one hit per distinct source tile.
    tile_keys = [hit.tile_key for hit in resp.hits]
    assert tile_keys == ["imagery/b.tif", "imagery/c.tif"]
    assert len(tile_keys) == len(set(tile_keys))
    # The best-scoring embedding of a duplicated tile wins.
    b_hit = next(h for h in resp.hits if h.tile_key == "imagery/b.tif")
    assert b_hit.embedding_key == "embeddings/j1/b.npy"
    assert b_hit.score == 0.9


def test_get_preset_defaults():
    assert get_preset("sentinel-2-rgb").band_count == 3
    assert get_preset("sentinel-2-l2a").band_count == 10
    assert get_preset("unknown-sensor").key == "sentinel-2-rgb"  # safe default


def test_select_device_without_torch_is_contained():
    """In the base venv (no torch) device selection raises the actionable error.

    Skipped when the ML stack is installed — that path is exercised live.
    """
    try:
        import torch  # noqa: F401

        pytest.skip("torch installed; base-venv degradation not under test")
    except ImportError:
        pass
    with pytest.raises(EngineUnavailableError):
        select_device("auto")
