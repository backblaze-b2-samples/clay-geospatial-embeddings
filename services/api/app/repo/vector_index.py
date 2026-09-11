"""usearch k-NN index built over embedding tensors loaded from B2.

The index is built on demand from every ``.npy`` under ``embeddings/`` (the
demo archive is small, so a per-query rebuild is cheap and always fresh). Both
``usearch`` and ``numpy`` are imported lazily so the base ``test:api`` venv can
still import this module.
"""

from app.repo.embeddings import list_embedding_keys, load_embedding


class VectorIndex:
    """A built usearch index plus the tile/embedding keys it was built from."""

    def __init__(self, index, embedding_keys: list[str], tile_map: dict[str, str]):
        self._index = index
        self.embedding_keys = embedding_keys
        # embedding_key -> tile_key, so a hit can name the source tile.
        self._tile_map = tile_map

    @property
    def size(self) -> int:
        return len(self.embedding_keys)

    def query(self, vector, k: int) -> list[tuple[str, str, float]]:
        """Return up to ``k`` (embedding_key, tile_key, score) tuples.

        Score is cosine similarity in [0, 1] (usearch returns cosine distance).
        """
        if self.size == 0:
            return []
        import numpy as np

        matches = self._index.search(np.asarray(vector, dtype="float32"), min(k, self.size))
        hits: list[tuple[str, str, float]] = []
        for key_id, distance in zip(matches.keys, matches.distances, strict=False):
            emb_key = self.embedding_keys[int(key_id)]
            score = max(0.0, 1.0 - float(distance))
            hits.append((emb_key, self._tile_map.get(emb_key, emb_key), score))
        return hits


def build_index(tile_map: dict[str, str] | None = None) -> VectorIndex:
    """Build a fresh index over all embeddings in B2.

    ``tile_map`` (embedding_key -> tile_key) is optional; when omitted the
    embedding key is echoed as the tile reference.
    """
    import numpy as np
    from usearch.index import Index

    keys = list_embedding_keys()
    if not keys:
        return VectorIndex(None, [], tile_map or {})

    vectors = [np.asarray(load_embedding(k), dtype="float32").ravel() for k in keys]
    ndim = int(vectors[0].shape[0])
    index = Index(ndim=ndim, metric="cos")
    index.add(np.arange(len(vectors)), np.vstack(vectors))
    return VectorIndex(index, keys, tile_map or {})
