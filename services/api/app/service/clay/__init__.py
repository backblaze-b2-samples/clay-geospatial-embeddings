"""Local Clay embedding engine (headline capability).

Public surface for the service layer: device selection, embedding a tile, and
the presets / errors the job runner needs.
"""

from app.service.clay.engine import (
    CLAY_CKPT,
    CLAY_HF_REPO,
    EngineUnavailableError,
    embed_pixels,
    reset_model_cache,
    select_device,
)
from app.service.clay.presets import PRESETS, SensorPresetDef, get_preset

__all__ = [
    "CLAY_CKPT",
    "CLAY_HF_REPO",
    "PRESETS",
    "EngineUnavailableError",
    "SensorPresetDef",
    "embed_pixels",
    "get_preset",
    "reset_model_cache",
    "select_device",
]
