"""Imagery Library — scoped asset explorer over the ``imagery/`` prefix.

Distinct from the never-removable full-bucket explorer: this lists only GeoTIFF
tiles under ``imagery/``, enriched with parsed geospatial metadata and served
with PNG thumbnails.
"""

from app.config.prefixes import IMAGERY_PREFIX
from app.repo import get_object_bytes, list_files
from app.service.geotiff import GeoTiffError, read_metadata, render_thumbnail
from app.types import ImageryItem

_TIFF_SUFFIXES = (".tif", ".tiff")
# Cap inline header parsing / thumbnail rendering so a huge tile can't blow the
# API's memory. Larger tiles still list, without metadata/thumbnail.
_PARSE_CAP_BYTES = 40 * 1024 * 1024


def _is_tile(key: str) -> bool:
    return key.lower().endswith(_TIFF_SUFFIXES)


def list_imagery(limit: int = 100) -> list[ImageryItem]:
    """List GeoTIFF tiles under ``imagery/`` with parsed metadata (newest first)."""
    files = [f for f in list_files(prefix=IMAGERY_PREFIX) if _is_tile(f.key)]
    files.sort(key=lambda f: f.uploaded_at, reverse=True)
    items: list[ImageryItem] = []
    for f in files[:limit]:
        metadata = None
        warning = None
        if f.size_bytes <= _PARSE_CAP_BYTES:
            try:
                metadata, warning = read_metadata(get_object_bytes(f.key))
            except RuntimeError as e:
                warning = f"Could not read tile: {e}"
        else:
            warning = "Tile too large to parse header inline."
        items.append(
            ImageryItem(
                key=f.key,
                filename=f.filename,
                size_bytes=f.size_bytes,
                size_human=f.size_human,
                uploaded_at=f.uploaded_at,
                metadata=metadata,
                metadata_warning=warning,
            )
        )
    return items


def get_thumbnail(key: str, size: int = 256) -> bytes:
    """Render a PNG thumbnail for one imagery tile. Raises GeoTiffError on failure."""
    if not key.startswith(IMAGERY_PREFIX) or not _is_tile(key):
        raise GeoTiffError("Thumbnails are only available for imagery/ GeoTIFF tiles")
    data = get_object_bytes(key)
    metadata, _ = read_metadata(data)
    band_count = metadata.band_count if metadata and metadata.band_count else 3
    # S2-like multiband tiles store blue,green,red first; RGB tiles store R,G,B.
    rgb = (2, 1, 0) if band_count >= 4 else (0, 1, 2)
    return render_thumbnail(data, rgb, size)
