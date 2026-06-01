#!/usr/bin/env python3
"""
Live listener for /sss_processor/processed.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Optional

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from geometry_msgs.msg import Quaternion
from blueboat_interfaces.msg import ProcessedSSSPing
from custom_functions import quaternion_to_yaw

import matplotlib.pyplot as plt


# ---------------------------------------------------------------------------
# Tuning constants
# ---------------------------------------------------------------------------
# Mosaic resolution. 25 cm/pixel is a good default for a small-boat survey
# at ~0.5-1 m/s where consecutive pings are ~5-30 cm apart along-track.
# Finer cells (10 cm) leave along-track gaps when the boat is slow; coarser
# (50 cm) loses across-track detail. Tune based on your typical survey speed.
CELL_SIZE_M: float = 0.25

# Initial mosaic extent (m). Grows automatically as the survey expands.
INITIAL_HALF_EXTENT_M: float = 50.0

# Display update cadence. Updating the figures on every ping at ~28 Hz is
# pointless and slows everything down -- redraw a few times per second.
REDRAW_EVERY_N_PINGS: int = 20

# Depth smoothing: simple moving-average over the last N pings.
DEPTH_SMOOTH_N: int = 15


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def project_to_world(
    robot_x: float, robot_y: float, yaw: float,
    y_local: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Rotate a ping's lateral samples into world coordinates.

    The ping is purely lateral in the boat frame: each sample sits at
    (x_body=0, y_body=y_local[i]). REP-103 conventions:
      * +y_body = port  -> processor publishes positive `port_y[i]`
      * -y_body = stbd  -> processor publishes negative `starboard_y[i]`

    The 2D rotation by yaw of (0, y_body) into world frame is:
        x_w = -sin(yaw) * y_body
        y_w =  cos(yaw) * y_body
    """
    x_world = robot_x - math.sin(yaw) * y_local
    y_world = robot_y + math.cos(yaw) * y_local
    return x_world, y_world


# ---------------------------------------------------------------------------
# Mosaic grid
# ---------------------------------------------------------------------------
class MosaicGrid:
    """Auto-growing 2D running-mean raster of sonar intensity.

    World extent is anchored at (0, 0) and grows in `chunk` increments as
    samples land outside the current bounds. Each cell stores (sum, count)
    so the displayed image is the mean intensity per cell.
    """

    def __init__(self, cell_size_m: float = CELL_SIZE_M,
                 initial_half_extent_m: float = INITIAL_HALF_EXTENT_M) -> None:
        self._cell = cell_size_m
        n = int(math.ceil(2 * initial_half_extent_m / cell_size_m))
        self._sum:   np.ndarray = np.zeros((n, n), dtype=np.float64)
        self._count: np.ndarray = np.zeros((n, n), dtype=np.uint32)
        # World coordinates of the lower-left corner of cell [0, 0].
        self._x0: float = -initial_half_extent_m
        self._y0: float = -initial_half_extent_m
        self._chunk = int(math.ceil(50.0 / cell_size_m))  # grow by 50 m

    @property
    def shape(self) -> tuple[int, int]:
        return self._sum.shape

    @property
    def extent(self) -> tuple[float, float, float, float]:
        h, w = self._sum.shape
        return (self._x0, self._x0 + w * self._cell,
                self._y0, self._y0 + h * self._cell)

    def _world_to_cell(self, x: np.ndarray, y: np.ndarray
                       ) -> tuple[np.ndarray, np.ndarray]:
        cx = ((x - self._x0) / self._cell).astype(np.int32)
        cy = ((y - self._y0) / self._cell).astype(np.int32)
        return cx, cy

    def _ensure_contains(self, xmin: float, xmax: float,
                         ymin: float, ymax: float) -> None:
        h, w = self._sum.shape
        pad_left = pad_right = pad_bot = pad_top = 0
        if xmin < self._x0:
            pad_left = int(math.ceil((self._x0 - xmin) / self._cell))
            pad_left = max(pad_left, self._chunk)
        if xmax >= self._x0 + w * self._cell:
            pad_right = int(math.ceil(
                (xmax - (self._x0 + w * self._cell)) / self._cell)) + 1
            pad_right = max(pad_right, self._chunk)
        if ymin < self._y0:
            pad_bot = int(math.ceil((self._y0 - ymin) / self._cell))
            pad_bot = max(pad_bot, self._chunk)
        if ymax >= self._y0 + h * self._cell:
            pad_top = int(math.ceil(
                (ymax - (self._y0 + h * self._cell)) / self._cell)) + 1
            pad_top = max(pad_top, self._chunk)
        if pad_left or pad_right or pad_bot or pad_top:
            self._sum = np.pad(
                self._sum, ((pad_bot, pad_top), (pad_left, pad_right))
            )
            self._count = np.pad(
                self._count, ((pad_bot, pad_top), (pad_left, pad_right))
            )
            self._x0 -= pad_left * self._cell
            self._y0 -= pad_bot * self._cell

    def add_samples(self, x: np.ndarray, y: np.ndarray,
                    intensity: np.ndarray) -> None:
        if x.size == 0:
            return
        self._ensure_contains(float(x.min()), float(x.max()),
                              float(y.min()), float(y.max()))
        cx, cy = self._world_to_cell(x, y)
        h, w = self._sum.shape
        ok = (cx >= 0) & (cx < w) & (cy >= 0) & (cy < h)
        # `np.add.at` does unbuffered scatter-add so duplicate (cx,cy)
        # indices accumulate properly.
        np.add.at(self._sum,   (cy[ok], cx[ok]), intensity[ok])
        np.add.at(self._count, (cy[ok], cx[ok]), 1)

    def render(self) -> np.ndarray:
        """Return the mean-intensity raster (NaN where no samples)."""
        with np.errstate(invalid="ignore", divide="ignore"):
            img = np.where(self._count > 0, self._sum / self._count, np.nan)
        return img

    def save(self, prefix: str | Path) -> tuple[Path, Path]:
        """Save raster as compact .npz and quick-look .png."""
        prefix = Path(prefix)
        img = self.render()
        npz_path = prefix.with_suffix(".npz")
        png_path = prefix.with_suffix(".png")
        np.savez_compressed(
            npz_path,
            mean_intensity=img.astype(np.float32),
            count=self._count,
            cell_size_m=self._cell,
            x0=self._x0,
            y0=self._y0,
        )
        # Quick-look PNG with sensible percentile contrast.
        valid = img[np.isfinite(img)]
        if valid.size > 0:
            vmin, vmax = np.percentile(valid, [2, 98])
        else:
            vmin, vmax = 0.0, 1.0
        plt.imsave(png_path, img,
                   origin="lower", cmap="copper", vmin=vmin, vmax=vmax)
        return npz_path, png_path


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------
class ProcessedSSSListener(Node):

    def __init__(self) -> None:
        super().__init__("processed_sss_listener")

        qos = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                         history=HistoryPolicy.KEEP_LAST, depth=10)
        self.create_subscription(
            ProcessedSSSPing, "/sss_processor/processed",
            self._on_processed_ping, qos,
        )

        self._mosaic = MosaicGrid()

        # Time series for depth + boat trajectory.
        self._t_first: Optional[float] = None
        self._depth_t: list[float] = []
        self._depth_z: list[float] = []
        self._traj_x:  list[float] = []
        self._traj_y:  list[float] = []

        self._ping_count = 0

        # ---- Matplotlib live figures (interactive) -----------------------
        plt.ion()
        self._fig_mosaic, self._ax_mosaic = plt.subplots(figsize=(8, 8))
        self._ax_mosaic.set_xlabel("X world (m)")
        self._ax_mosaic.set_ylabel("Y world (m)")
        self._ax_mosaic.set_title("Side-scan mosaic")
        self._ax_mosaic.set_aspect("equal")
        self._ax_mosaic.grid(True, alpha=0.3)
        self._mosaic_im = None
        self._traj_line, = self._ax_mosaic.plot(
            [], [], "-", color="cyan", linewidth=1.2, label="boat track"
        )
        self._traj_marker, = self._ax_mosaic.plot(
            [], [], "o", color="white", markeredgecolor="red", markersize=6,
        )
        self._ax_mosaic.legend(loc="upper right")

        self._fig_depth, self._ax_depth = plt.subplots(figsize=(8, 3.5))
        self._ax_depth.set_xlabel("Time since first ping (s)")
        self._ax_depth.set_ylabel("Depth (m)")
        self._ax_depth.set_title("Estimated seabed depth")
        self._ax_depth.grid(True, alpha=0.3)
        self._depth_raw_line,    = self._ax_depth.plot(
            [], [], color="steelblue", linewidth=0.6, alpha=0.4, label="raw")
        self._depth_smooth_line, = self._ax_depth.plot(
            [], [], color="darkred", linewidth=1.5, label=f"smoothed (N={DEPTH_SMOOTH_N})")
        self._ax_depth.legend(loc="upper right")
        # Depth increases downward in marine convention.
        self._ax_depth.invert_yaxis()

        self.get_logger().info(
            f"listener ready: cell={CELL_SIZE_M*100:.0f} cm, "
            f"redraw every {REDRAW_EVERY_N_PINGS} pings"
        )

    # ----- callback -----------------------------------------------------
    def _on_processed_ping(self, msg: ProcessedSSSPing) -> None:
        # Robot pose snapshot.
        rx, ry = float(msg.robot_x), float(msg.robot_y)
        yaw = quaternion_to_yaw(msg.robot_orientation)

        # Project both sides into world frame -- the sign of y_local
        # encodes the side (port=+, stbd=-) so one rotation suffices.
        port_y      = np.asarray(msg.port_y,                dtype=np.float64)
        port_db     = np.asarray(msg.port_intensity_db,     dtype=np.float32)
        stbd_y      = np.asarray(msg.starboard_y,           dtype=np.float64)
        stbd_db     = np.asarray(msg.starboard_intensity_db, dtype=np.float32)

        all_y_local = np.concatenate([port_y, stbd_y])
        all_db      = np.concatenate([port_db, stbd_db])
        xw, yw = project_to_world(rx, ry, yaw, all_y_local)

        self._mosaic.add_samples(xw, yw, all_db)

        # Time series.
        t_now = msg.port_stamp.sec + msg.port_stamp.nanosec * 1e-9
        if self._t_first is None:
            self._t_first = t_now
        self._depth_t.append(t_now - self._t_first)
        self._depth_z.append(float(msg.water_depth))
        self._traj_x.append(rx)
        self._traj_y.append(ry)

        self._ping_count += 1
        if self._ping_count % REDRAW_EVERY_N_PINGS == 0:
            self._redraw()

    # ----- drawing ------------------------------------------------------
    def _redraw(self) -> None:
        img = self._mosaic.render()
        valid = img[np.isfinite(img)]
        if valid.size == 0:
            return
        vmin, vmax = np.percentile(valid, [2, 98])
        extent = self._mosaic.extent

        if self._mosaic_im is None:
            self._mosaic_im = self._ax_mosaic.imshow(
                img, origin="lower", extent=extent,
                cmap="copper", vmin=vmin, vmax=vmax,
                interpolation="nearest",
            )
        else:
            self._mosaic_im.set_data(img)
            self._mosaic_im.set_extent(extent)
            self._mosaic_im.set_clim(vmin, vmax)

        # Trajectory overlay + current position marker.
        self._traj_line.set_data(self._traj_x, self._traj_y)
        self._traj_marker.set_data([self._traj_x[-1]], [self._traj_y[-1]])
        self._ax_mosaic.relim()
        self._ax_mosaic.autoscale_view()

        # Depth (raw + smoothed).
        self._depth_raw_line.set_data(self._depth_t, self._depth_z)
        if len(self._depth_z) >= DEPTH_SMOOTH_N:
            kernel = np.ones(DEPTH_SMOOTH_N) / DEPTH_SMOOTH_N
            smoothed = np.convolve(self._depth_z, kernel, mode="valid")
            # Align smoothed values with their centre time.
            offset = DEPTH_SMOOTH_N // 2
            t_smooth = self._depth_t[offset:offset + len(smoothed)]
            self._depth_smooth_line.set_data(t_smooth, smoothed)
        self._ax_depth.relim()
        self._ax_depth.autoscale_view()

        self._fig_mosaic.canvas.draw_idle()
        self._fig_mosaic.canvas.flush_events()
        self._fig_depth.canvas.draw_idle()
        self._fig_depth.canvas.flush_events()

    # ----- save ---------------------------------------------------------
    def save(self) -> None:
        npz_path, png_path = self._mosaic.save("sonar_mosaic")
        self.get_logger().info(
            f"saved mosaic: {png_path} (preview)  {npz_path} (data)"
        )
        # Boat trajectory + depth CSV (small file: O(num_pings), not O(samples)).
        traj_path = Path("boat_trajectory.csv")
        with open(traj_path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t_since_first_s", "x_m", "y_m", "depth_m"])
            for t, x, y, z in zip(self._depth_t, self._traj_x,
                                  self._traj_y, self._depth_z):
                w.writerow([f"{t:.3f}", f"{x:.3f}", f"{y:.3f}", f"{z:.3f}"])
        self.get_logger().info(f"saved trajectory: {traj_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(args=None) -> None:
    rclpy.init(args=args)
    node = ProcessedSSSListener()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("CTRL+C detected")
        node.save()
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
