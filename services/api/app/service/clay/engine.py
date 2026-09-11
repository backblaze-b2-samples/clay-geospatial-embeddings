"""Local Clay foundation-model embedding engine (headline capability).

Runs Clay's *own* model (https://github.com/Clay-foundation/model) on-device to
turn imagery tiles into geospatial embedding vectors. No substitute model is
used. torch + claymodel live in ``requirements-ml.txt`` and are imported lazily;
if they are missing (base ``test:api`` venv), every entry point raises
``EngineUnavailableError`` so a run is recorded as ``failed`` rather than 500ing.

Device rule (hard): autodetect CUDA -> Apple MPS -> CPU, defaulting to CPU.
Clay/PyTorch MPS op coverage is partial, so we enable the runtime MPS->CPU
fallback and also retry a failed MPS/CUDA embed on CPU (see service/jobs.py).
"""

import logging
import os
import threading

# Must be set before torch is ever imported so unsupported MPS ops silently run
# on CPU instead of raising. Harmless on non-MPS hosts.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

from app.service.clay.datacube import build_datacube
from app.service.clay.presets import SensorPresetDef

logger = logging.getLogger(__name__)

# HuggingFace repo + checkpoint for Clay v1.5 (public — no HF_TOKEN required).
CLAY_HF_REPO = "made-with-clay/Clay"
CLAY_CKPT = "v1.5/clay-v1.5.ckpt"
CLAY_MODEL_SIZE = "large"

_model_lock = threading.Lock()
# device -> loaded model. Cached so a multi-tile run loads Clay once.
_models: dict[str, object] = {}


class EngineUnavailableError(RuntimeError):
    """The Clay ML stack (torch/claymodel) is not installed or failed to load.

    Carries an actionable message naming the install step so the failed job
    record tells the user exactly what to do.
    """


def select_device(preference: str = "auto") -> str:
    """Resolve the compute device: CUDA -> MPS -> CPU, defaulting to CPU.

    An explicit preference (cpu/cuda/mps) is honoured when available, else it
    falls back to CPU. Requires torch; raises EngineUnavailableError otherwise.
    """
    try:
        import torch
    except ImportError as e:  # pragma: no cover - exercised only without ML deps
        raise EngineUnavailableError(_INSTALL_HINT) from e

    pref = (preference or "auto").strip().lower()
    cuda = torch.cuda.is_available()
    mps = getattr(torch.backends, "mps", None) is not None and torch.backends.mps.is_available()

    if pref == "cuda":
        return "cuda" if cuda else "cpu"
    if pref == "mps":
        return "mps" if mps else "cpu"
    if pref == "cpu":
        return "cpu"
    # auto
    if cuda:
        return "cuda"
    if mps:
        return "mps"
    return "cpu"


_INSTALL_HINT = (
    "Clay ML stack not installed. Install the engine deps with "
    "`services/api/.venv/bin/pip install -r services/api/requirements-ml.txt` "
    "(torch + claymodel), then re-run the job."
)


def _load_model(device: str):
    """Load (and cache) Clay v1.5 on ``device``. Raises EngineUnavailableError."""
    with _model_lock:
        cached = _models.get(device)
        if cached is not None:
            return cached
        try:
            import torch
            from claymodel.module import ClayMAEModule
            from huggingface_hub import hf_hub_download
        except ImportError as e:
            raise EngineUnavailableError(_INSTALL_HINT) from e

        try:
            ckpt_path = hf_hub_download(repo_id=CLAY_HF_REPO, filename=CLAY_CKPT)
            # The checkpoint is the official Clay release we just downloaded, so
            # trust it through torch>=2.6's weights_only default.
            orig_load = torch.load

            def _trusting_load(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return orig_load(*args, **kwargs)

            torch.load = _trusting_load
            try:
                model = ClayMAEModule.load_from_checkpoint(
                    ckpt_path,
                    model_size=CLAY_MODEL_SIZE,
                    mask_ratio=0.0,
                    shuffle=False,
                )
            finally:
                torch.load = orig_load
            model.eval()
            model.to(device)
        except EngineUnavailableError:
            raise
        except Exception as e:
            raise EngineUnavailableError(
                f"Failed to load Clay v1.5 on {device}: {e}"
            ) from e

        _models[device] = model
        logger.info("Loaded Clay v1.5 (%s) on device=%s", CLAY_MODEL_SIZE, device)
        return model


def embed_pixels(pixels, preset: SensorPresetDef, device: str, **cube_kwargs):
    """Embed one tile's pixel array (C, H, W) into a 1-D numpy vector.

    Raises EngineUnavailableError if the stack is missing or inference fails.
    """
    try:
        import torch
    except ImportError as e:
        raise EngineUnavailableError(_INSTALL_HINT) from e

    model = _load_model(device)
    datacube = build_datacube(pixels, preset, device, **cube_kwargs)
    try:
        with torch.no_grad():
            encoded = model.model.encoder(datacube)
        # Clay's encoder returns (patch_embeddings, ...); the class token at
        # position 0 is the tile-level embedding.
        patches = encoded[0] if isinstance(encoded, (tuple, list)) else encoded
        vector = patches[:, 0, :].detach().to("cpu").numpy()[0]
    except Exception as e:
        raise EngineUnavailableError(f"Clay inference failed on {device}: {e}") from e
    return vector


def reset_model_cache() -> None:
    """Drop cached models (used by tests and after a device switch)."""
    with _model_lock:
        _models.clear()
