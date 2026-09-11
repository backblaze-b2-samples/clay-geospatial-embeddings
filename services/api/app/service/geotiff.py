"""GeoTIFF reading: geospatial metadata, band pixels, and PNG thumbnails.

rasterio (and its GDAL wheel) plus numpy/Pillow live in ``requirements-ml.txt``
and are imported lazily, so this module imports cleanly in the base test venv.
Callers get a typed result or a warning string — a tile whose header cannot be
parsed still lists, it just carries a warning instead of metadata.
"""

import io
import logging

from app.types import GeoTiffMetadata

logger = logging.getLogger(__name__)

_GEO_DEPS_HINT = (
    "GeoTIFF support not installed — install services/api/requirements-ml.txt "
    "(rasterio) to read imagery metadata and thumbnails."
)


class GeoTiffError(RuntimeError):
    """Raised when the geospatial stack is missing or a tile can't be read."""


def read_metadata(data: bytes) -> tuple[GeoTiffMetadata | None, str | None]:
    """Parse GeoTIFF header fields. Returns (metadata, warning).

    Never raises for a bad tile: a parse failure yields (None, warning) so the
    Imagery Library can still list the object.
    """
    try:
        import rasterio
    except ImportError:
        return None, _GEO_DEPS_HINT
    try:
        with rasterio.io.MemoryFile(data) as mem, mem.open() as ds:
            transform = ds.transform
            bounds = ds.bounds
            return (
                GeoTiffMetadata(
                    width=ds.width,
                    height=ds.height,
                    band_count=ds.count,
                    crs=str(ds.crs) if ds.crs else None,
                    bounds=[bounds.left, bounds.bottom, bounds.right, bounds.top],
                    gsd=abs(transform.a) if transform else None,
                    dtype=str(ds.dtypes[0]) if ds.dtypes else None,
                ),
                None,
            )
    except Exception as e:
        logger.warning("GeoTIFF metadata read failed", exc_info=True)
        return None, f"Could not read GeoTIFF header: {e}"


def read_pixels(data: bytes, band_count: int):
    """Read the first ``band_count`` bands as a (C, H, W) numpy array.

    Raises GeoTiffError if the stack is missing or the tile has too few bands.
    """
    try:
        import numpy as np
        import rasterio
    except ImportError as e:
        raise GeoTiffError(_GEO_DEPS_HINT) from e
    try:
        with rasterio.io.MemoryFile(data) as mem, mem.open() as ds:
            if ds.count < band_count:
                raise GeoTiffError(
                    f"Tile has {ds.count} band(s); preset needs {band_count}"
                )
            bands = ds.read(list(range(1, band_count + 1)))
            return np.asarray(bands, dtype="float32")
    except GeoTiffError:
        raise
    except Exception as e:
        raise GeoTiffError(f"Could not read GeoTIFF pixels: {e}") from e


def render_thumbnail(data: bytes, rgb_indices: tuple[int, int, int], size: int = 256) -> bytes:
    """Render a small PNG thumbnail from the given RGB band indices (0-based).

    Percentile-stretched per band for a legible preview. Raises GeoTiffError if
    the stack is missing or the tile can't be rendered.
    """
    try:
        import numpy as np
        import rasterio
        from PIL import Image
    except ImportError as e:
        raise GeoTiffError(_GEO_DEPS_HINT) from e
    try:
        with rasterio.io.MemoryFile(data) as mem, mem.open() as ds:
            count = ds.count
            idx = [min(i, count - 1) + 1 for i in rgb_indices]
            bands = ds.read(idx).astype("float32")  # (3, H, W)
        out = np.zeros_like(bands)
        for c in range(bands.shape[0]):
            lo, hi = np.percentile(bands[c], (2, 98))
            if hi <= lo:
                hi = lo + 1
            out[c] = np.clip((bands[c] - lo) / (hi - lo), 0, 1) * 255
        rgb = np.transpose(out.astype("uint8"), (1, 2, 0))
        img = Image.fromarray(rgb, mode="RGB")
        img.thumbnail((size, size))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception as e:
        raise GeoTiffError(f"Could not render thumbnail: {e}") from e
