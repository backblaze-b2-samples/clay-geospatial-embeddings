"""Sensor / band presets for building the Clay datacube.

Each preset describes the bands fed to Clay's encoder: their centre wavelengths
(micrometres), the ground sample distance (metres/pixel), which channels form an
RGB thumbnail, and an approximate per-band reflectance normalization
(mean / std). The wavelengths and GSD follow the public Sentinel-2 / NAIP band
definitions; the mean/std are reflectance-scale approximations of Clay's
published metadata and can be replaced with the exact values from
``claymodel``'s ``metadata.yaml`` for production-fidelity embeddings.

Kept in the service layer (no boto3, no torch) so it imports cleanly in the
base test venv.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SensorPresetDef:
    key: str
    label: str
    # Clay platform id the bands belong to.
    platform: str
    band_names: list[str]
    # Centre wavelength per band, micrometres (order matches band_names).
    waves: list[float]
    # Ground sample distance, metres/pixel.
    gsd: float
    # Indices into band_names used to render an RGB thumbnail (R, G, B).
    rgb_indices: tuple[int, int, int]
    # Divide raw pixel values by this to reach ~[0, 1] reflectance.
    scale: float
    # Approximate reflectance mean/std per band (order matches band_names).
    mean: list[float] = field(default_factory=list)
    std: list[float] = field(default_factory=list)

    @property
    def band_count(self) -> int:
        return len(self.band_names)


_S2_L2A = SensorPresetDef(
    key="sentinel-2-l2a",
    label="Sentinel-2 L2A (multispectral)",
    platform="sentinel-2-l2a",
    band_names=["blue", "green", "red", "re1", "re2", "re3", "nir", "nir08", "swir16", "swir22"],
    waves=[0.493, 0.560, 0.665, 0.704, 0.740, 0.783, 0.842, 0.865, 1.610, 2.190],
    gsd=10.0,
    rgb_indices=(2, 1, 0),
    scale=10000.0,
    mean=[0.13, 0.13, 0.12, 0.14, 0.19, 0.22, 0.24, 0.25, 0.20, 0.14],
    std=[0.09, 0.09, 0.10, 0.10, 0.11, 0.12, 0.13, 0.13, 0.12, 0.10],
)

_S2_RGB = SensorPresetDef(
    key="sentinel-2-rgb",
    label="Sentinel-2 RGB",
    platform="sentinel-2-l2a",
    band_names=["red", "green", "blue"],
    waves=[0.665, 0.560, 0.493],
    gsd=10.0,
    rgb_indices=(0, 1, 2),
    scale=10000.0,
    mean=[0.12, 0.13, 0.13],
    std=[0.10, 0.09, 0.09],
)

_NAIP_RGB = SensorPresetDef(
    key="naip-rgb",
    label="NAIP RGB",
    platform="naip",
    band_names=["red", "green", "blue"],
    waves=[0.640, 0.550, 0.470],
    gsd=1.0,
    rgb_indices=(0, 1, 2),
    scale=255.0,
    mean=[0.42, 0.42, 0.40],
    std=[0.20, 0.19, 0.19],
)

PRESETS: dict[str, SensorPresetDef] = {
    _S2_RGB.key: _S2_RGB,
    _S2_L2A.key: _S2_L2A,
    _NAIP_RGB.key: _NAIP_RGB,
}


def get_preset(key: str) -> SensorPresetDef:
    """Look up a preset by key, defaulting to Sentinel-2 RGB."""
    return PRESETS.get(key, _S2_RGB)
