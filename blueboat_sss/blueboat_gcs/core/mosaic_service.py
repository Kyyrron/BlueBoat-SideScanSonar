"""Mosaic service: connects the ping stream to the map raster.

Runs entirely in the GUI thread (fed by queued signals):

* on every ``SonarPing`` (~28 Hz): project the pre-corrected lateral
  samples to world coordinates (reused ``project_to_world``) and
  scatter-add them into the reused ``MosaicGrid`` — a sub-millisecond
  numpy operation;
* on a QTimer at ``render_hz`` (default 4 Hz): if the grid changed,
  render mean intensities (optionally gap-filled) to a QImage and emit
  ``raster_updated`` for the map layer. Decoupling ingestion from
  rendering is what keeps the GUI smooth at any ping rate.

Interpolation is applied at render time only; the grid and the saved
``.npz`` always contain raw data (see mapping/interpolation.py).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from ..config.settings import AppConfig
from ..mapping.interpolation import fill_small_gaps
from ..mapping.mosaic import MosaicGrid, project_to_world
from ..mapping.renderer import MosaicRenderer
from ..models.sonar import SonarPing


class MosaicService(QObject):
    """Owns the mosaic grid; produces display rasters and saved artifacts."""

    #: QImage, extent (xmin, xmax, ymin, ymax), cell size [m]
    raster_updated = Signal(QImage, tuple, float)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._grid = MosaicGrid(
            cell_size_m=config.mosaic.cell_size_m,
            initial_half_extent_m=config.mosaic.initial_half_extent_m)
        self._renderer = MosaicRenderer(
            percentiles=tuple(config.mosaic.contrast_percentiles))
        self._interpolate = False
        self._depth_t: list[float] = []
        self._depth_z: list[float] = []
        self._traj: list[Tuple[float, float]] = []
        self._t_first: Optional[float] = None

        self._timer = QTimer(self)
        self._timer.setInterval(int(1000.0 / config.mosaic.render_hz))
        self._timer.timeout.connect(self._render_if_dirty)
        self._timer.start()

    # ---- ingestion ------------------------------------------------------------
    def on_sonar_ping(self, ping: SonarPing) -> None:
        xw, yw = project_to_world(ping.robot_x, ping.robot_y, ping.yaw,
                                  ping.y_local)
        self._grid.add_samples(xw, yw, ping.intensity_db)
        if self._t_first is None:
            self._t_first = ping.t
        self._depth_t.append(ping.t - self._t_first)
        self._depth_z.append(ping.water_depth)
        self._traj.append((ping.robot_x, ping.robot_y))

    # ---- display -----------------------------------------------------------------
    def set_interpolation(self, enabled: bool) -> None:
        if enabled != self._interpolate:
            self._interpolate = enabled
            self._force_render()

    def _render_if_dirty(self) -> None:
        if self._grid.consume_dirty():
            self._force_render()

    def _force_render(self) -> None:
        mean = self._grid.render()
        if not np.isfinite(mean).any():
            return
        if self._interpolate:
            mean, _mask = fill_small_gaps(
                mean, self._grid.count, self._grid.cell_size_m,
                max_gap_m=self._config.interpolation.max_gap_m,
                min_neighbors=self._config.interpolation.min_neighbors)
        image = self._renderer.to_qimage(mean)
        self.raster_updated.emit(image, self._grid.extent,
                                 self._grid.cell_size_m)

    # ---- persistence (same artifacts as the legacy listener) ---------------------
    def save(self) -> Optional[Path]:
        """Save mosaic .npz/.png + trajectory/depth CSV; returns the dir."""
        if self._t_first is None:
            return None
        stamp = datetime.today().strftime("%Y_%m_%d-%H_%M")
        log_root = Path(self._config.data_root).expanduser() / stamp
        self._grid.save(log_root)  # raw data only, never interpolated
        import csv
        with open(log_root / "boat_trajectory.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_since_first_s", "x_m", "y_m", "depth_m"])
            for t, (x, y), z in zip(self._depth_t, self._traj, self._depth_z):
                w.writerow([f"{t:.3f}", f"{x:.3f}", f"{y:.3f}", f"{z:.3f}"])
        return log_root
