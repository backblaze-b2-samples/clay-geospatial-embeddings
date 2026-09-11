"""REST surface for Embedding Jobs (the primary entity: all verbs).

Handlers are sync `def` so blocking B2 I/O runs in Starlette's threadpool; the
long-running `run` is dispatched to the threadpool explicitly.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.service.jobs import (
    JobConflictError,
    JobNotFoundError,
    create_job,
    delete_job,
    get_job,
    list_jobs,
    list_source_prefixes,
    run_job,
    update_job,
)
from app.types import JobCreateRequest, JobRecord, JobUpdateRequest

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", response_model=list[JobRecord])
def list_jobs_endpoint():
    return list_jobs()


# Declared before /jobs/{job_id} so the static path isn't captured as an id.
@router.get("/jobs/source-prefixes", response_model=list[str])
def source_prefixes_endpoint():
    """Discovered sub-prefixes under imagery/ for the create-form selector."""
    return list_source_prefixes()


@router.post("/jobs", response_model=JobRecord)
def create_job_endpoint(req: JobCreateRequest):
    return create_job(req)


@router.get("/jobs/{job_id}", response_model=JobRecord)
def get_job_endpoint(job_id: str):
    try:
        return get_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.patch("/jobs/{job_id}", response_model=JobRecord)
def update_job_endpoint(job_id: str, req: JobUpdateRequest):
    try:
        return update_job(job_id, req)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except JobConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None


@router.delete("/jobs/{job_id}")
def delete_job_endpoint(job_id: str):
    try:
        delete_job(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except JobConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to delete job") from None
    logger.info("Job deleted: id=%s", job_id)
    return {"deleted": True, "id": job_id}


@router.post("/jobs/{job_id}/run", response_model=JobRecord)
async def run_job_endpoint(job_id: str):
    """Run the embedding pipeline. Returns the final job record.

    A run may take a while on CPU; the browser shows a pending state until it
    resolves. Engine failures are captured in the returned record (status
    `failed`), not raised as 500s.
    """
    try:
        return await run_in_threadpool(run_job, job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    except JobConflictError as e:
        raise HTTPException(status_code=409, detail=e.detail) from None
