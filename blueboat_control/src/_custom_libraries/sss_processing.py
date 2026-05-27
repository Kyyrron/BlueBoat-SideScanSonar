#!/usr/bin/env python3
"""Pure-math helpers and trackers for side scan sonar post-processing.

No ROS or hardware dependencies -- independently importable and unit-testable.
"""

from __future__ import annotations

import math
from collections import deque
from typing import Deque, List, Optional, Sequence, Tuple


def scale_to_db(
    pwr_u16: Sequence[int], min_pwr_db: float, max_pwr_db: float
) -> List[float]:
    """Convert raw u16 power samples to dB.

    Formula (Cerulean Omniscan 450 template):
        db = min_pwr_db + (raw / 65535) * (max_pwr_db - min_pwr_db)

    See: github.com/bluerobotics/ping-python/blob/master/generate/templates/omniscan450.py.in
    """
    span = max_pwr_db - min_pwr_db
    return [min_pwr_db + (s / 65535.0) * span for s in pwr_u16]


def detect_fbr_slant_m(
    pwr_db: Sequence[float],
    start_mm: int,
    length_mm: int,
    num_results: int,
    noise_floor_window: int,
    threshold_delta_db: float,
    persistence: int,
) -> Optional[float]:
    """First-Bottom-Return detection on a single ping (dB samples).

    Returns the slant range in meters of the first sample whose power rises
    `threshold_delta_db` above the early-ping noise floor and stays there
    for `persistence` consecutive samples. Returns None if no such sample
    exists.
    """
    n = len(pwr_db)
    if n < noise_floor_window + persistence:
        return None
    noise = sum(pwr_db[:noise_floor_window]) / noise_floor_window
    threshold = noise + threshold_delta_db
    denom = max(num_results - 1, 1)
    for i in range(noise_floor_window, n - persistence + 1):
        if pwr_db[i] <= threshold:
            continue
        if all(pwr_db[i + k] > threshold for k in range(persistence)):
            slant_mm = start_mm + (i / denom) * length_mm
            return slant_mm / 1000.0
    return None


def project_side(
    pwr_db: Sequence[float],
    start_mm: int,
    length_mm: int,
    num_results: int,
    altitude_m: float,
    transducer_y_offset_m: float,
    side_sign: float,
) -> Tuple[List[float], List[float]]:
    """Slant-range-correct one side, drop water-column samples.

    Returns (y_in_base_link, intensities_db); sample i of one list pairs
    with sample i of the other. `side_sign` = +1 for port, -1 for starboard.

    Assumes the seabed is locally flat under each ping (standard SSS
    practice with single-beam data).
    """
    y_out: List[float] = []
    db_out: List[float] = []
    start_m = start_mm / 1000.0
    length_m = length_mm / 1000.0
    denom = max(num_results - 1, 1)
    for i in range(len(pwr_db)):
        slant = start_m + (i / denom) * length_m
        if slant <= altitude_m:
            continue  # water column
        ground = math.sqrt(slant * slant - altitude_m * altitude_m)
        y_out.append(float(side_sign * (transducer_y_offset_m + ground)))
        db_out.append(float(pwr_db[i]))
    return y_out, db_out


class FBRTracker:
    """Cross-ping altitude estimator with bootstrap and last-known fallback.

    Per-ping inputs are the FBR slant ranges from each side. They are fused
    with max() so the seabed depth is never under-estimated (which would
    create false 'holes' in the survey area).

    Bootstrap: hold off until `bootstrap_pings` consecutive ping pairs
    produce an estimate AND those estimates span <= `agreement_tol_m`. The
    bootstrap altitude is the mean of those estimates.

    Operational: a successful per-ping estimate replaces the current
    altitude. A failed detection (no FBR on either side) keeps the last
    known value.
    """

    def __init__(self, bootstrap_pings: int, agreement_tol_m: float) -> None:
        self._bootstrap_pings = bootstrap_pings
        self._agreement_tol_m = agreement_tol_m
        # maxlen turns this into a sliding window -- once the earliest entry
        # falls out the new one takes its place, so bootstrap retries
        # naturally with the latest N estimates.
        self._window: Deque[float] = deque(maxlen=bootstrap_pings)
        self._altitude: Optional[float] = None

    @property
    def is_bootstrapped(self) -> bool:
        return self._altitude is not None

    @property
    def altitude(self) -> Optional[float]:
        return self._altitude

    def update(
        self, port_alt: Optional[float], stbd_alt: Optional[float]
    ) -> Optional[float]:
        if port_alt is not None and stbd_alt is not None:
            candidate: Optional[float] = max(port_alt, stbd_alt)
        elif port_alt is not None:
            candidate = port_alt
        elif stbd_alt is not None:
            candidate = stbd_alt
        else:
            candidate = None

        if self._altitude is None:
            # Bootstrap phase.
            if candidate is None:
                # A failed ping breaks the run -- start over.
                self._window.clear()
                return None
            self._window.append(candidate)
            if len(self._window) == self._bootstrap_pings:
                spread = max(self._window) - min(self._window)
                if spread <= self._agreement_tol_m:
                    self._altitude = sum(self._window) / self._bootstrap_pings
            return self._altitude
        # Operational phase.
        if candidate is not None:
            self._altitude = candidate
        return self._altitude
