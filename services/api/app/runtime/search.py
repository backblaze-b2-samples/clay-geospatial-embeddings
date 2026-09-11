"""REST surface for similarity search (k-NN scene retrieval over embeddings)."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.service.search import SearchUnavailableError, search_by_key
from app.types import SearchByKeyRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search_endpoint(req: SearchByKeyRequest):
    """Embed the query tile with Clay and return its nearest neighbours.

    Blocking (model + index) work runs in the threadpool. A missing engine or an
    empty archive answers with an actionable 4xx/5xx, never a bare 500.
    """
    try:
        return await run_in_threadpool(search_by_key, req)
    except SearchUnavailableError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
