"""REST surface for the Imagery Library (scoped GeoTIFF explorer over imagery/)."""

import logging

from fastapi import APIRouter, HTTPException, Response

from app.service.geotiff import GeoTiffError
from app.service.library import get_thumbnail, list_imagery
from app.types import ImageryItem

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/library", response_model=list[ImageryItem])
def list_library_endpoint(limit: int = 100):
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
    try:
        return list_imagery(limit=limit)
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to list imagery") from None


@router.get("/library/thumbnail")
def library_thumbnail_endpoint(key: str, size: int = 256):
    """PNG thumbnail for one imagery tile (referenced directly by <img>)."""
    if size < 32 or size > 1024:
        raise HTTPException(status_code=400, detail="size must be between 32 and 1024")
    try:
        png = get_thumbnail(key, size=size)
    except GeoTiffError as e:
        raise HTTPException(status_code=415, detail=str(e)) from None
    except RuntimeError:
        raise HTTPException(status_code=502, detail="Failed to read tile") from None
    return Response(content=png, media_type="image/png")
