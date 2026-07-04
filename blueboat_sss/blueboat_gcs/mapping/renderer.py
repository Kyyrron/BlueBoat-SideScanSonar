"""Mosaic raster -> displayable RGBA image.

Design decisions
----------------
* The renderer runs on a GUI-side QTimer at ``mosaic.render_hz`` (default
  4 Hz), fully decoupled from the ~28 Hz ping rate: ingestion is a cheap
  numpy scatter-add per ping, drawing is a bounded-rate raster refresh.
  This is what removes the flicker/slowdown of the matplotlib listener.
* Contrast stretching keeps the field-proven 2–98 percentile scheme of
  the old listener, but percentiles are computed on a subsample of valid
  cells so the cost stays flat as the survey grows.
* Empty cells are fully transparent (alpha 0) so the satellite layer
  shows through — the SSS mosaic always remains the top data layer.
* The colormap is a numpy implementation of matplotlib's "copper" so the
  application does not depend on matplotlib.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from PySide6.QtGui import QImage

_LUT: Optional[np.ndarray] = None


def copper_lut() -> np.ndarray:
    """256x3 uint8 'copper' colormap (R=min(1,1.25x), G=.7812x, B=.4975x)."""
    global _LUT
    if _LUT is None:
        x = np.linspace(0.0, 1.0, 256)
        lut = np.stack([np.clip(1.25 * x, 0, 1), 0.7812 * x, 0.4975 * x],
                       axis=1)
        _LUT = (lut * 255).astype(np.uint8)
    return _LUT


class MosaicRenderer:
    """Converts a (mean, filled_mask) raster into an RGBA8888 QImage."""

    def __init__(self, percentiles: Tuple[float, float] = (2.0, 98.0),
                 max_percentile_samples: int = 200_000) -> None:
        self._p = percentiles
        self._max_samples = max_percentile_samples

    def _limits(self, img: np.ndarray) -> Tuple[float, float]:
        valid = img[np.isfinite(img)]
        if valid.size == 0:
            return 0.0, 1.0
        if valid.size > self._max_samples:  # keep percentile cost bounded
            step = valid.size // self._max_samples
            valid = valid[::step]
        vmin, vmax = np.percentile(valid, self._p)
        if vmax - vmin < 1e-6:
            vmax = vmin + 1e-6
        return float(vmin), float(vmax)

    def to_qimage(self, mean: np.ndarray) -> QImage:
        """Raster (row 0 = ymin, NaN = empty) -> QImage (row 0 = ymax)."""
        vmin, vmax = self._limits(mean)
        finite = np.isfinite(mean)
        norm = np.zeros_like(mean, dtype=np.float32)
        norm[finite] = np.clip((mean[finite] - vmin) / (vmax - vmin), 0.0, 1.0)

        idx = (norm * 255).astype(np.uint8)
        rgba = np.zeros((*mean.shape, 4), dtype=np.uint8)
        rgba[..., :3] = copper_lut()[idx]
        rgba[..., 3] = np.where(finite, 255, 0)

        # World row 0 is ymin ('origin=lower'); QImage row 0 is drawn at the
        # top, and the map view maps scene-y-down to world-y-up, so flip.
        rgba = np.ascontiguousarray(np.flipud(rgba))
        h, w = rgba.shape[:2]
        img = QImage(rgba.data, w, h, 4 * w, QImage.Format_RGBA8888)
        return img.copy()  # detach from the numpy buffer lifetime
