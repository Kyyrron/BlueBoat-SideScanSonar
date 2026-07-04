"""Sonar configuration.

Two layers, mirroring the real system exactly:

* **Acquisition parameters** -- the same six run-dependent parameters the
  real ``sss_node.py`` exposes (``range_start_mm``, ``range_length_mm``,
  ``msec_per_ping``, ``gain_index``, ``num_results``, ``pulse_len_percent``);
  identical names, identical semantics (``msec_per_ping = 0`` -> free-run).

* **Simulation-only parameters** -- sensor geometry, acoustic model and
  noise knobs that a real operator does not control (the physics of the
  device and of the water). These live under the ``model:`` key of
  ``default_sonar.yaml`` and never leak into the ROS message content.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

SPEED_OF_SOUND_MPS = 1500.0
OMNISCAN_FREQ_HZ = 451_127          # observed on the real device
DEVICE_PROCESSING_MS = 2.0          # free-run overhead beyond two-way travel


@dataclass
class AcquisitionParams:
    """Run-dependent parameters, identical to the real node's ROS params."""

    range_start_mm: int = 0
    range_length_mm: int = 15_000
    msec_per_ping: int = 0                 # 0 = free-run (device behaviour)
    gain_index: int = 4
    num_results: int = 600
    pulse_len_percent: float = 0.002

    @property
    def range_max_m(self) -> float:
        return (self.range_start_mm + self.range_length_mm) / 1000.0

    @property
    def bin_size_m(self) -> float:
        return self.range_length_mm / 1000.0 / max(self.num_results, 1)

    def ping_period_s(self) -> float:
        """Effective ping period: commanded, floored by two-way travel time
        plus device processing -- matches the observed 22 ms at 15 m."""
        two_way = 2.0 * self.range_max_m / SPEED_OF_SOUND_MPS
        free_run = two_way + DEVICE_PROCESSING_MS / 1000.0
        return max(self.msec_per_ping / 1000.0, free_run)

    def pulse_duration_s(self) -> float:
        """Device convention: pulse length as a fraction of the ping window."""
        return self.pulse_len_percent * self.ping_period_s()


@dataclass
class SonarModelConfig:
    """Simulation-only sensor/acoustics/noise parameters."""

    # Mounting geometry (vehicle frame; z below waterline).
    sensor_depth_m: float = 0.15           # transducer below surface
    mount_x_m: float = 0.0                 # fore/aft offset from base_link
    mount_y_abs_m: float = 0.20            # lateral offset magnitude per side
    beam_tilt_deg: float = 20.0            # pattern centre below horizontal
    vertical_aperture_deg: float = 55.0    # -3 dB two-sided vertical fan
    horizontal_aperture_deg: float = 0.5   # along-track beamwidth

    # Acoustic model.
    lambert_exponent: float = 1.7          # default when material info absent
    absorption_db_per_m: float = 0.10      # ~450 kHz seawater
    spreading_exponent: float = 2.0        # amplitude spreading (two-way)
    tvg_compensation: float = 0.90         # 0..1 fraction of range loss the
                                           # "device" gain removes
    calibration_db_offset: float = 16.0    # max_pwr_db = 10log10(pwr)+offset
    base_scale: float = 18_000.0           # linear power -> u16 counts at gain 4
    gain_index_step_db: float = 3.0        # counts scaling per gain index step

    # Noise model.
    speckle: bool = True
    noise_floor: float = 0.004             # relative to base_scale
    gain_drift_amp: float = 0.06           # slow multiplicative drift +-
    gain_drift_period_s: float = 45.0
    dropped_ping_prob: float = 0.003
    watercolumn_noise: float = 0.02        # relative noise in r < altitude bins

    # Ground-line sampling.
    sample_step_m: float = 0.05

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SonarModelConfig":
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        unknown = set(d) - known
        if unknown:
            raise KeyError(f"Unknown sonar model keys: {sorted(unknown)}")
        return cls(**{k: v for k, v in d.items()})


@dataclass
class SonarConfig:
    acquisition: AcquisitionParams = field(default_factory=AcquisitionParams)
    model: SonarModelConfig = field(default_factory=SonarModelConfig)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "SonarConfig":
        with open(path, "r", encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        acq = doc.get("acquisition", {})
        model = doc.get("model", {})
        known_acq = {f.name for f in AcquisitionParams.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        bad = set(acq) - known_acq
        if bad:
            raise KeyError(f"Unknown acquisition keys: {sorted(bad)}")
        return cls(acquisition=AcquisitionParams(**acq),
                   model=SonarModelConfig.from_dict(model))
