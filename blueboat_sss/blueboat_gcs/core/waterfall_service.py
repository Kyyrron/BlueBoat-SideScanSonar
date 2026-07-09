"""Waterfall service: raw pings stacked in acquisition order.

Rendering strategy (decision)
-----------------------------
The waterfall is *not* a map layer: its axes are ping index (vertical,
time) × across-track distance (horizontal), i.e. the raw acquisition
domain — the domain in which future AI datasets will be generated. It
therefore gets its own numpy ring buffer and its own view widget instead
of being forced into the georeferenced QGraphicsScene.

* Each incoming ping is resampled onto a fixed number of across-track
  columns spanning its own full swath (port left, starboard right —
  matching SonarView row layout; per-row scaling is exactly how a raw
  waterfall behaves when the range setting changes mid-survey).
* Rows live in a preallocated ``(rows, columns)`` float32 ring buffer:
  ingestion is O(columns) per ping, memory is constant, and the newest
  ping is always the bottom row.
* Rendering reuses the *same* ``MosaicRenderer``/``DisplaySettings``
  pipeline as the mosaic on the same throttled QTimer cadence — one
  value→pixel path for both views, so the display controls behave
  identically everywhere.

Raw data is never modified; interpolation does not apply here (there are
no spatial gaps in the acquisition domain).
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from ..config.settings import AppConfig
from ..mapping.renderer import DisplaySettings, MosaicRenderer
from ..models.sonar import SonarPing


class WaterfallService(QObject):
    """Ring buffer of the most recent pings, rendered on a throttle."""

    #: QImage (row 0 = oldest ping, last row = newest), current range [m]
    image_updated = Signal(QImage, float)

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._rows = int(config.mosaic.waterfall_rows)
        self._cols = int(config.mosaic.waterfall_columns)
        self._buf = np.full((self._rows, self._cols), np.nan,
                            dtype=np.float32)
        self._head = 0                  # next row to write
        self._filled = 0                # rows written so far (<= _rows)
        self._range_m = 0.0             # current per-side swath [m]
        self._dirty = False
        self._enabled = False           # render only while the view is shown
        self._renderer = MosaicRenderer(
            percentiles=tuple(config.mosaic.contrast_percentiles))

        self._timer = QTimer(self)
        self._timer.setInterval(int(1000.0 / config.mosaic.render_hz))
        self._timer.timeout.connect(self._render_if_dirty)
        self._timer.start()

    # ---- ingestion -------------------------------------------------------------
    def on_sonar_ping(self, ping: SonarPing) -> None:
        y = ping.y_local
        if y.size < 2:
            return
        r = float(np.abs(y).max())
        if r <= 0.0:
            return
        self._range_m = r
        # Across-track column: port (+y) on the LEFT, starboard on the right.
        col = np.clip(((r - y) / (2.0 * r) * (self._cols - 1)).astype(np.int32),
                      0, self._cols - 1)
        row = np.full(self._cols, np.nan, dtype=np.float32)
        row[col] = ping.intensity_db          # duplicates: last sample wins
        self._buf[self._head] = row
        self._head = (self._head + 1) % self._rows
        self._filled = min(self._filled + 1, self._rows)
        self._dirty = True

    # ---- display -----------------------------------------------------------------
    def set_enabled(self, enabled: bool) -> None:
        """Called when the view mode switches; renders eagerly on entry."""
        self._enabled = enabled
        if enabled:
            self._force_render()

    def clear(self) -> None:
        """'Clear SSS data': drop the buffered pings; keep streaming."""
        self._buf.fill(np.nan)
        self._head = 0
        self._filled = 0
        self._dirty = False
        self.image_updated.emit(QImage(), self._range_m)  # null -> view clears

    # ---- persistence -----------------------------------------------------------
    def chronological(self) -> Optional[np.ndarray]:
        """Raw buffer rows, oldest first (None if empty)."""
        if self._filled == 0:
            return None
        if self._filled < self._rows:
            return self._buf[:self._filled].copy()
        return np.roll(self._buf, -self._head, axis=0)

    def export_into(self, target) -> bool:
        """Write waterfall.png (display pipeline) + waterfall_raw.npz
        (untouched buffer, for AI dataset generation) into ``target``."""
        chrono = self.chronological()
        if chrono is None:
            return False
        from pathlib import Path
        import cv2
        target = Path(target)
        target.mkdir(parents=True, exist_ok=True)
        rgba = self._renderer.to_rgba(chrono)
        cv2.imwrite(str(target / "waterfall.png"),
                    cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
        np.savez_compressed(target / "waterfall_raw.npz",
                            intensity_db=chrono,
                            swath_half_range_m=self._range_m,
                            columns=self._cols)
        return True

    def set_display(self, settings: DisplaySettings) -> None:
        self._renderer.settings = settings
        if self._enabled:
            self._force_render()

    def _render_if_dirty(self) -> None:
        if self._enabled and self._dirty:
            self._force_render()

    def _force_render(self) -> None:
        self._dirty = False
        if self._filled == 0:
            return
        # Chronological order, oldest first; newest ping = last row.
        if self._filled < self._rows:
            chrono = self._buf[:self._filled]
        else:
            chrono = np.roll(self._buf, -self._head, axis=0)
        img = self._renderer.to_qimage(chrono, flip=False)
        self.image_updated.emit(img, self._range_m)
