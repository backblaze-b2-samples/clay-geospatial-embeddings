"""Build a Clay datacube from a single imagery tile.

Clay's encoder consumes a dict of tensors: ``pixels`` (B, C, H, W), band-centre
``waves`` (C,), ``gsd`` (scalar), ``time`` (week/hour sin-cos) and ``latlon``
(sin-cos). This module turns a normalized pixel array + a sensor preset into
that dict. torch and numpy are imported lazily so the module imports without the
ML stack.
"""

from __future__ import annotations

import math
from datetime import datetime

from app.service.clay.presets import SensorPresetDef


def normalize_pixels(pixels, preset: SensorPresetDef):
    """Standardize raw band pixels to Clay's expected input.

    ``pixels`` is (C, H, W). Raw values are divided by the preset scale to reach
    reflectance, then standardized per band with the preset mean/std. Robust to
    both real reflectance rasters and the synthetic seed tiles.
    """
    import numpy as np

    arr = np.asarray(pixels, dtype="float32")
    if arr.ndim == 2:
        arr = arr[None, :, :]
    channels = arr.shape[0]
    scaled = arr / float(preset.scale)
    mean = np.asarray((preset.mean or [0.0] * channels)[:channels], dtype="float32")
    std = np.asarray((preset.std or [1.0] * channels)[:channels], dtype="float32")
    # Guard against a zero std.
    std = np.where(std == 0, 1.0, std)
    return (scaled - mean[:, None, None]) / std[:, None, None]


def _normalize_timestamp(date: datetime) -> tuple[list[float], list[float]]:
    week = date.isocalendar().week * 2 * math.pi / 52
    hour = date.hour * 2 * math.pi / 24
    return [math.sin(week), math.cos(week)], [math.sin(hour), math.cos(hour)]


def _normalize_latlon(lat: float, lon: float) -> tuple[list[float], list[float]]:
    lat_r = lat * math.pi / 180
    lon_r = lon * math.pi / 180
    return [math.sin(lat_r), math.cos(lat_r)], [math.sin(lon_r), math.cos(lon_r)]


def build_datacube(
    pixels,
    preset: SensorPresetDef,
    device: str,
    *,
    lat: float = 0.0,
    lon: float = 0.0,
    date: datetime | None = None,
):
    """Assemble the Clay encoder input dict for one tile on ``device``."""
    import torch

    normed = normalize_pixels(pixels, preset)
    date = date or datetime(2024, 6, 1, 10, 0, 0)
    week, hour = _normalize_timestamp(date)
    lat_v, lon_v = _normalize_latlon(lat, lon)

    def t(data, dtype=torch.float32):
        return torch.tensor(data, dtype=dtype, device=device)

    return {
        "platform": preset.platform,
        "pixels": t(normed).unsqueeze(0),
        "time": t([week + hour]),
        "latlon": t([lat_v + lon_v]),
        "waves": t(preset.waves),
        "gsd": t(preset.gsd),
    }
