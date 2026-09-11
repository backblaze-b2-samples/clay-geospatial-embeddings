"""Persist Embedding Job records as JSON in B2 (``jobs/<id>.json``).

No database — B2 is the sole store for the primary entity (build-constraints:
"B2 objects can be the sole store"). This module deals in plain dicts; the
service layer validates them into ``JobRecord`` models.
"""

import json

from app.config.prefixes import JOBS_PREFIX
from app.repo.b2_object import get_object_bytes
from app.repo.objects import delete_key, list_keys, object_exists, put_bytes


def job_key(job_id: str) -> str:
    return f"{JOBS_PREFIX}{job_id}.json"


def save_job(job_id: str, record: dict) -> None:
    """Write (or overwrite) a job record. Raises RuntimeError on S3 failure."""
    payload = json.dumps(record, default=str, indent=2).encode("utf-8")
    put_bytes(job_key(job_id), payload, "application/json")


def load_job(job_id: str) -> dict | None:
    """Load one job record, or None if it does not exist."""
    key = job_key(job_id)
    if not object_exists(key):
        return None
    return json.loads(get_object_bytes(key))


def list_jobs() -> list[dict]:
    """Load every job record under ``jobs/``. Skips anything unparseable."""
    records: list[dict] = []
    for key in list_keys(JOBS_PREFIX):
        if not key.endswith(".json"):
            continue
        try:
            records.append(json.loads(get_object_bytes(key)))
        except (RuntimeError, ValueError):
            continue
    return records


def delete_job(job_id: str) -> None:
    """Delete a job's JSON record. Raises RuntimeError on S3 failure."""
    delete_key(job_key(job_id))
