"""Canonical B2 object-key prefixes for the geospatial pipeline.

One place so the repo and service layers never drift on where each artifact
class lives in the bucket. Everything the app writes is namespaced under one of
these, which is also what keeps the scoped Imagery Library and the per-job
delete honest (a job only ever deletes under its own ``embeddings/<id>/``).
"""

# Raw / ingested GeoTIFF imagery tiles (upload + seed land here).
IMAGERY_PREFIX = "imagery/"
# Normalized tile cache written during an embedding run (reused on re-run).
TILES_PREFIX = "tiles/"
# Embedding tensors: embeddings/<job_id>/<tile>.npy
EMBEDDINGS_PREFIX = "embeddings/"
# Job records: jobs/<id>.json
JOBS_PREFIX = "jobs/"

__all__ = [
    "EMBEDDINGS_PREFIX",
    "IMAGERY_PREFIX",
    "JOBS_PREFIX",
    "TILES_PREFIX",
]
