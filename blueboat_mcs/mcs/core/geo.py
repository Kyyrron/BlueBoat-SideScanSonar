"""Online georeferencing between the ROS local/world frame and GPS.

``robot_interface.py`` defines the world frame with an origin and yaw offset
(``lat0``, ``lon0``, ``yaw0``) that are internal to that node and never
published.  Rather than duplicating or modifying robot-side logic, the
station *estimates* the same rigid transform online: it collects
simultaneous pairs of (odom XY, GPS position projected to local
east/north metres) and fits a 2-D rotation + translation with the Kabsch
algorithm once the vehicle has moved enough for the problem to be
well-conditioned.

The result enables:
* GPS read-out of any clicked map point,
* placement of the satellite tile layer,
* GPS display for the pinger world position,

with an explicit quality flag (RMS residual) shown to the operator.

Web-mercator helpers for the tile layer also live here.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from mcs.config.settings import GeoConfig
from mcs.core.series import TimeSeries

EARTH_RADIUS_M = 6378137.0


# ----------------------------------------------------------------- lat/lon
def latlon_to_local_en(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Equirectangular projection of (lat, lon) to metres east/north of (lat0, lon0)."""
    east = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    north = math.radians(lat - lat0) * EARTH_RADIUS_M
    return east, north


def local_en_to_latlon(east: float, north: float, lat0: float, lon0: float) -> tuple[float, float]:
    lat = lat0 + math.degrees(north / EARTH_RADIUS_M)
    lon = lon0 + math.degrees(east / (EARTH_RADIUS_M * math.cos(math.radians(lat0))))
    return lat, lon


# -------------------------------------------------------------- web mercator
def latlon_to_tile_xy(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Fractional slippy-map tile coordinates for a lat/lon at a zoom level."""
    lat = max(min(lat, 85.05112878), -85.05112878)
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.log(math.tan(lat_r) + 1.0 / math.cos(lat_r)) / math.pi) / 2.0 * n
    return x, y


def tile_xy_to_latlon(x: float, y: float, zoom: int) -> tuple[float, float]:
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n))))
    return lat, lon


def metres_per_pixel(lat: float, zoom: int, tile_px: int = 256) -> float:
    return (2 * math.pi * EARTH_RADIUS_M * math.cos(math.radians(lat))) / (tile_px * 2 ** zoom)


# ------------------------------------------------------------- georeferencer
@dataclass
class GeoFit:
    """World(x,y) = R(theta) @ EN + t  is inverted here: EN = R(-theta)(world - t)."""

    theta: float          # rotation from local-EN frame to world frame
    tx: float             # world-frame offset
    ty: float
    lat0: float           # projection origin (first GPS fix)
    lon0: float
    rms_m: float          # fit residual
    n_pairs: int

    # world -> lat/lon
    def world_to_latlon(self, x: float, y: float) -> tuple[float, float]:
        c, s = math.cos(-self.theta), math.sin(-self.theta)
        dx, dy = x - self.tx, y - self.ty
        east = c * dx - s * dy
        north = s * dx + c * dy
        return local_en_to_latlon(east, north, self.lat0, self.lon0)

    def latlon_to_world(self, lat: float, lon: float) -> tuple[float, float]:
        east, north = latlon_to_local_en(lat, lon, self.lat0, self.lon0)
        c, s = math.cos(self.theta), math.sin(self.theta)
        return c * east - s * north + self.tx, s * east + c * north + self.ty


class GeoReferencer:
    """Accumulates (world XY, GPS) pairs and maintains the best-fit transform."""

    def __init__(self, cfg: GeoConfig) -> None:
        self._cfg = cfg
        self._pairs = TimeSeries(dim=4)  # x, y, east, north
        self._lat0: float | None = None
        self._lon0: float | None = None
        self._fit: GeoFit | None = None
        self._last_fit_t: float = -1e18

    @property
    def fit(self) -> GeoFit | None:
        return self._fit

    @property
    def is_valid(self) -> bool:
        return self._fit is not None and self._fit.rms_m <= self._cfg.max_residual_m

    def add_pair(self, t: float, x: float, y: float, lat: float, lon: float) -> None:
        """Feed a simultaneous odom position and GPS fix (called ~ GPS rate)."""
        if lat == 0.0 and lon == 0.0:  # NavSatFix with no fix
            return
        if self._lat0 is None:
            self._lat0, self._lon0 = lat, lon
        east, north = latlon_to_local_en(lat, lon, self._lat0, self._lon0)
        self._pairs.append(t, (x, y, east, north))
        if t - self._last_fit_t >= self._cfg.refit_period_s:
            self._last_fit_t = t
            self._refit(t)

    # ------------------------------------------------------------- internal
    def _refit(self, now: float) -> None:
        ts, vs = self._pairs.window(now - self._cfg.fit_window_s, now + 1.0)
        if len(ts) < self._cfg.min_pairs:
            return
        world = vs[:, 0:2]
        en = vs[:, 2:4]
        spread = float(np.linalg.norm(world.max(axis=0) - world.min(axis=0)))
        if spread < self._cfg.min_spread_m:
            return  # not enough motion, rotation unobservable

        # Kabsch: rotation aligning EN onto world (scale fixed to 1: both metres)
        wc = world - world.mean(axis=0)
        ec = en - en.mean(axis=0)
        h = ec.T @ wc
        u, _, vt = np.linalg.svd(h)
        d = np.sign(np.linalg.det(vt.T @ u.T))
        r = vt.T @ np.diag([1.0, d]) @ u.T
        theta = math.atan2(r[1, 0], r[0, 0])
        t = world.mean(axis=0) - r @ en.mean(axis=0)
        residual = world - (en @ r.T + t)
        rms = float(np.sqrt(np.mean(np.sum(residual ** 2, axis=1))))
        assert self._lat0 is not None and self._lon0 is not None
        self._fit = GeoFit(
            theta=theta, tx=float(t[0]), ty=float(t[1]),
            lat0=self._lat0, lon0=self._lon0, rms_m=rms, n_pairs=len(ts),
        )
