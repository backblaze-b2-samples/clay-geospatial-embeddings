"""Embedding Job lifecycle tests (hermetic — B2 store mocked in memory)."""

import pytest

from app.service import jobs as jobs_svc
from app.types import JobConfig, JobCreateRequest, JobUpdateRequest


@pytest.fixture
def mem_store(monkeypatch):
    """Replace the B2-backed job store with an in-memory dict."""
    store: dict[str, dict] = {}
    monkeypatch.setattr(jobs_svc, "save_job", lambda jid, rec: store.__setitem__(jid, rec))
    monkeypatch.setattr(jobs_svc, "load_job", lambda jid: store.get(jid))
    monkeypatch.setattr(jobs_svc, "_list_job_records", lambda: list(store.values()))
    monkeypatch.setattr(jobs_svc, "_delete_job_record", lambda jid: store.pop(jid, None))
    monkeypatch.setattr(jobs_svc, "delete_prefix", lambda prefix: 0)
    monkeypatch.setattr(jobs_svc, "list_keys", lambda prefix: [])
    return store


def test_create_read_update_delete(mem_store):
    rec = jobs_svc.create_job(
        JobCreateRequest(name="  sentinel2-tirana  ", config=JobConfig(tile_size=512))
    )
    assert rec.status == "pending"
    assert rec.name == "sentinel2-tirana"  # trimmed
    assert rec.config.tile_size == 512

    got = jobs_svc.get_job(rec.id)
    assert got.id == rec.id

    upd = jobs_svc.update_job(rec.id, JobUpdateRequest(name="renamed"))
    assert upd.name == "renamed"
    assert upd.config.tile_size == 512  # unchanged

    assert len(jobs_svc.list_jobs()) == 1

    jobs_svc.delete_job(rec.id)
    with pytest.raises(jobs_svc.JobNotFoundError):
        jobs_svc.get_job(rec.id)


def test_get_missing_raises(mem_store):
    with pytest.raises(jobs_svc.JobNotFoundError):
        jobs_svc.get_job("nope")


def test_run_no_tiles_marks_failed(mem_store):
    rec = jobs_svc.create_job(JobCreateRequest(name="empty"))
    result = jobs_svc.run_job(rec.id)
    assert result.status == "failed"
    assert "No .tif" in result.message
    assert result.duration_seconds is not None


def test_run_without_engine_marks_failed(mem_store, monkeypatch):
    """With tiles present but no Clay stack, the run fails gracefully (no 500)."""
    monkeypatch.setattr(jobs_svc, "list_keys", lambda prefix: ["imagery/a.tif"])
    monkeypatch.setattr(jobs_svc, "get_object_bytes", lambda key: b"not-a-real-tiff")
    rec = jobs_svc.create_job(JobCreateRequest(name="run"))
    result = jobs_svc.run_job(rec.id)
    assert result.status == "failed"
    # Either the ML stack is missing (base venv) or a real device resolved and a
    # later step failed on the fake tile — both are contained, not raised.
    assert result.message
    assert result.status != "running"
