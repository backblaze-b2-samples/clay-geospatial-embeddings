"""Read/write Clay embedding tensors (.npy) in B2 under ``embeddings/<job_id>/``.

numpy is imported lazily inside the functions so the base ``test:api`` venv (no
``requirements-ml.txt``) can still import this module — only an actual embed /
search touches numpy.
"""

import hashlib
import io

from app.config.prefixes import EMBEDDINGS_PREFIX
from app.repo.b2_object import get_object_bytes
from app.repo.objects import list_keys, put_bytes


def embedding_key(job_id: str, tile_key: str) -> str:
    """Stable, collision-resistant key for a tile's embedding within a job.

    The tile key can contain slashes and odd characters, so it is hashed into a
    flat filename under the job's own prefix.
    """
    digest = hashlib.sha1(tile_key.encode("utf-8")).hexdigest()[:16]
    return f"{EMBEDDINGS_PREFIX}{job_id}/{digest}.npy"


def save_embedding(key: str, vector) -> None:
    """Serialize a 1-D numpy vector to ``.npy`` bytes and store it in B2."""
    import numpy as np

    buf = io.BytesIO()
    np.save(buf, np.asarray(vector, dtype="float32"))
    put_bytes(key, buf.getvalue(), "application/octet-stream")


def load_embedding(key: str):
    """Load a ``.npy`` embedding from B2 as a numpy array."""
    import numpy as np

    return np.load(io.BytesIO(get_object_bytes(key)))


def list_embedding_keys(prefix: str = EMBEDDINGS_PREFIX) -> list[str]:
    """Every embedding ``.npy`` key under ``prefix`` (default: all embeddings)."""
    return [k for k in list_keys(prefix) if k.endswith(".npy")]
