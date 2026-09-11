"""Seed a small set of synthetic RGB GeoTIFF tiles into B2 under ``imagery/``.

Makes the whole pipeline reproducible from a fresh clone with no multi-TB
download and no licensing concerns: a handful of tiny, license-clean tiles that
Clay can embed and similarity search can rank. Tiles are generated in three
visually/spectrally distinct scene classes (forest / water / urban) so k-NN
retrieval returns same-class neighbours rather than noise.

Requires the geospatial stack: install services/api/requirements-ml.txt first.
Reads B2 credentials from the repo-root .env exactly like the app.

Usage:
    services/api/.venv/bin/python services/api/scripts/seed_imagery.py
    services/api/.venv/bin/python services/api/scripts/seed_imagery.py --per-class 4 --size 256
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

# Import the app's settings + repo write path (repo-root .env) like setup_b2_cors.
API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.config import settings  # noqa: E402
from app.config.prefixes import IMAGERY_PREFIX  # noqa: E402
from app.repo.objects import put_bytes  # noqa: E402

# Per-class base reflectance (scaled to ~0-10000 DN) for R, G, B and the texture
# character. Distinct enough that Clay embeds them into separable clusters.
CLASSES = {
    "forest": {"rgb": (900, 2200, 1100), "texture": 700, "smooth": False},
    "water": {"rgb": (500, 900, 2600), "texture": 200, "smooth": True},
    "urban": {"rgb": (2600, 2500, 2400), "texture": 1500, "smooth": False},
}


def _scene(rng: np.random.Generator, base_rgb, texture: int, smooth: bool, size: int):
    """Build a (3, size, size) uint16 RGB scene for one class."""
    bands = []
    # A smooth low-frequency gradient plus per-class high-frequency texture.
    yy, xx = np.mgrid[0:size, 0:size].astype("float32") / size
    gradient = (0.6 + 0.4 * np.sin(3 * xx) * np.cos(3 * yy))
    for base in base_rgb:
        noise = rng.normal(0, texture, size=(size, size)).astype("float32")
        if smooth:
            # Cheap blur: average with shifted copies to calm the water texture.
            noise = (noise + np.roll(noise, 1, 0) + np.roll(noise, 1, 1)) / 3
        band = base * gradient + noise
        bands.append(np.clip(band, 0, 10000))
    return np.stack(bands).astype("uint16")


def _to_geotiff(arr: np.ndarray, gsd: float = 10.0) -> bytes:
    """Encode a (3, H, W) array as an in-memory GeoTIFF (UTM 33N, 10 m GSD)."""
    _, height, width = arr.shape
    # Nominal origin near Tirana, Albania in UTM 33N — real CRS + bounds so the
    # Imagery Library shows meaningful geospatial metadata.
    transform = from_origin(400000, 4600000, gsd, gsd)
    profile = {
        "driver": "GTiff",
        "dtype": "uint16",
        "count": arr.shape[0],
        "height": height,
        "width": width,
        "crs": "EPSG:32633",
        "transform": transform,
        "compress": "deflate",
    }
    with rasterio.io.MemoryFile() as mem:
        with mem.open(**profile) as ds:
            ds.write(arr)
        return mem.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-class", type=int, default=3, help="tiles per scene class")
    parser.add_argument("--size", type=int, default=256, help="tile edge length in pixels")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    args = parser.parse_args()

    if not settings.b2_bucket_name:
        sys.stderr.write("B2_BUCKET_NAME is not set — configure .env first.\n")
        return 2

    rng = np.random.default_rng(args.seed)
    written = 0
    for name, spec in CLASSES.items():
        for i in range(1, args.per_class + 1):
            arr = _scene(rng, spec["rgb"], spec["texture"], spec["smooth"], args.size)
            data = _to_geotiff(arr)
            key = f"{IMAGERY_PREFIX}{name}-{i:02d}.tif"
            put_bytes(key, data, "image/tiff")
            sys.stdout.write(f"seeded {key} ({len(data)} bytes)\n")
            written += 1

    sys.stdout.write(
        f"\nDone. Seeded {written} tiles under '{IMAGERY_PREFIX}' in "
        f"bucket '{settings.b2_bucket_name}'.\n"
        "Next: create an Embedding Job (Sentinel-2 RGB) and run it, then try "
        "similarity search.\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
