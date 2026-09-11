"""Imagery Library models — scoped GeoTIFF gallery over ``imagery/``."""

from datetime import datetime

from pydantic import BaseModel


class GeoTiffMetadata(BaseModel):
    """Geospatial header fields read from a GeoTIFF (rasterio).

    Every field is optional: a tile whose header cannot be parsed (or when the
    geospatial stack is not installed) still lists, with these left null and a
    warning on the item.
    """

    width: int | None = None
    height: int | None = None
    band_count: int | None = None
    crs: str | None = None
    # Bounding box in the tile's CRS: [left, bottom, right, top].
    bounds: list[float] | None = None
    # Ground sample distance (metres/pixel), from the affine transform.
    gsd: float | None = None
    dtype: str | None = None


class ImageryItem(BaseModel):
    """One tile in the Imagery Library."""

    key: str
    filename: str
    size_bytes: int
    size_human: str
    uploaded_at: datetime
    # Presigned inline URL for the PNG thumbnail preview endpoint is built
    # client-side from the key; here we carry the parsed geospatial metadata.
    metadata: GeoTiffMetadata | None = None
    metadata_warning: str | None = None
