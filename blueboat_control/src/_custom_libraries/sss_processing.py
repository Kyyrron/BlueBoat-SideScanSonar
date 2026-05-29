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


class _SideTracker:
    """Single-side altitude tracker bootstrapped from temporal self-consistency.

    A side is considered locked once `bootstrap_pings` of its most recent
    detections all fall within `agreement_tol_m` of each other (a stable,
    plausible seabed return) -- it does NOT need to agree with the other
    side. This makes the system robust to one transducer (e.g. a low-gain
    channel) returning noise: the good side carries the estimate alone.

    After lock, each new detection within `outlier_tol_m` of the current
    altitude updates it; detections further away are rejected as outliers
    (a fish, a rock edge, a noise spike) and the last value is held. A
    long run of rejects (longer than `relock_after`) forces a re-bootstrap,
    so the tracker recovers if the seabed genuinely steps.
    """

    def __init__(self, bootstrap_pings: int, agreement_tol_m: float,
                 outlier_tol_m: float, relock_after: int) -> None:
        self._bootstrap_pings = bootstrap_pings
        self._agreement_tol_m = agreement_tol_m
        self._outlier_tol_m = outlier_tol_m
        self._relock_after = relock_after
        self._window: Deque[float] = deque(maxlen=bootstrap_pings)
        self._altitude: Optional[float] = None
        self._reject_streak = 0
        self._miss_streak = 0

    @property
    def altitude(self) -> Optional[float]:
        return self._altitude

    @property
    def locked(self) -> bool:
        return self._altitude is not None

    def update(self, fbr: Optional[float]) -> Optional[float]:
        if self._altitude is None:
            # --- bootstrap phase ---
            # An occasional missed detection (None) shouldn't wipe progress;
            # we just don't add to the window. Because the window is a
            # fixed-size sliding deque, stale early values age out on their
            # own, so a slowly-drifting seabed still locks once the most
            # recent `bootstrap_pings` detections are mutually consistent.
            if fbr is None:
                self._miss_streak += 1
                # Only a long blackout (no bottom at all) clears progress.
                if self._miss_streak >= self._relock_after:
                    self._window.clear()
                    self._miss_streak = 0
                return None
            self._miss_streak = 0
            self._window.append(fbr)
            if len(self._window) == self._bootstrap_pings:
                if (max(self._window) - min(self._window)) <= self._agreement_tol_m:
                    self._altitude = sum(self._window) / len(self._window)
            return self._altitude

        # --- operational phase ---
        if fbr is None:
            self._reject_streak += 1
        elif abs(fbr - self._altitude) <= self._outlier_tol_m:
            self._altitude = fbr
            self._reject_streak = 0
        else:
            self._reject_streak += 1

        if self._reject_streak >= self._relock_after:
            # Lost the bottom -- drop the lock and re-bootstrap.
            self._altitude = None
            self._window.clear()
            self._reject_streak = 0
            self._miss_streak = 0
        return self._altitude


class FBRTracker:
    """Dual-side altitude estimator: each side bootstraps independently.

    Per-ping inputs are the FBR slant ranges from each side. Each side runs
    its own `_SideTracker`; the fused altitude is the max() of whichever
    sides are currently locked (max so the seabed is never under-estimated,
    which would push samples into the water column and create false holes).

    The critical property vs the old design: bootstrap no longer requires
    the two sides to agree with each other. If one transducer is low-gain
    and returns noise, the other side bootstraps and carries the estimate
    by itself. The system produces an altitude as soon as EITHER side is
    self-consistent for `bootstrap_pings` detections.
    """

    def __init__(self, bootstrap_pings: int, agreement_tol_m: float,
                 outlier_tol_m: float = 1.0, relock_after: int = 15) -> None:
        self._port = _SideTracker(bootstrap_pings, agreement_tol_m,
                                  outlier_tol_m, relock_after)
        self._stbd = _SideTracker(bootstrap_pings, agreement_tol_m,
                                  outlier_tol_m, relock_after)
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
        p = self._port.update(port_alt)
        s = self._stbd.update(stbd_alt)

        if p is not None and s is not None:
            self._altitude = max(p, s)
        elif p is not None:
            self._altitude = p
        elif s is not None:
            self._altitude = s
        # else: neither side locked -- keep last altitude (may be None during
        # initial bootstrap, or a held value if both sides transiently lost
        # the bottom before re-locking).
        return self._altitude
