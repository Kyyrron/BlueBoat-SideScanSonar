"""Acoustic response model for the geometric SSS renderer.

Assumptions (documented, deliberately simple -- see docs/sonar_model.md):

* Straight-ray propagation (no refraction; valid for short shallow ranges).
* Lambertian-family backscatter:  BS = rho * cos(theta_i)^p, where theta_i
  is the local incidence angle and p a material/global exponent.
* Two-way loss = geometric spreading (1/r^k) x absorption (alpha dB/m),
  partially compensated by an idealised device TVG (fraction ``tvg``),
  leaving a realistic residual range-dependent brightness falloff.
* Vertical beam pattern: Gaussian in depression angle around the mounted
  tilt; the pattern rides on the vehicle roll (surface-motion signature,
  contribution C4 of the thesis).

All functions are vectorised over range samples of one ping.
"""

from __future__ import annotations

import numpy as np

from .config import SonarModelConfig


def backscatter(reflectivity: np.ndarray, cos_incidence: np.ndarray,
                lambert_exponent: float) -> np.ndarray:
    """Per-sample backscatter strength (linear amplitude units)."""
    return reflectivity * np.power(np.clip(cos_incidence, 0.0, 1.0),
                                   lambert_exponent)


def beam_weight(depression_rad: np.ndarray, cfg: SonarModelConfig,
                roll_toward_side: float) -> np.ndarray:
    """Vertical beam pattern weight in [0, 1].

    ``depression_rad``: angle of the ray below horizontal (0 = horizontal,
    pi/2 = straight down). ``roll_toward_side``: vehicle roll projected onto
    this side's look direction (positive = fan pushed downward)."""
    center = np.radians(cfg.beam_tilt_deg) + roll_toward_side
    sigma = np.radians(cfg.vertical_aperture_deg) / 2.355  # FWHM -> sigma
    return np.exp(-0.5 * ((depression_rad - center) / max(sigma, 1e-6)) ** 2)


def two_way_loss(slant_range: np.ndarray, cfg: SonarModelConfig) -> np.ndarray:
    """Combined spreading + absorption loss (linear, <= 1)."""
    r = np.maximum(slant_range, 0.05)
    spreading = r ** (-cfg.spreading_exponent)
    absorption = 10.0 ** (-2.0 * cfg.absorption_db_per_m * r / 10.0)
    return spreading * absorption


def tvg_gain(slant_range: np.ndarray, cfg: SonarModelConfig) -> np.ndarray:
    """Idealised device time-varying gain: removes a fraction ``tvg`` of the
    modelled two-way loss (in dB), so residual falloff remains."""
    loss = two_way_loss(slant_range, cfg)
    return loss ** (-cfg.tvg_compensation)


def net_range_response(slant_range: np.ndarray, cfg: SonarModelConfig) -> np.ndarray:
    """loss x TVG in one call (numerically stable combined form)."""
    return two_way_loss(slant_range, cfg) ** (1.0 - cfg.tvg_compensation)
