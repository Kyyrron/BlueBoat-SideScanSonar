#!/usr/bin/env python3
"""
Side Scan Sonar processor node for the BlueBoat.

Consumes raw `OmniscanProfile` packets from the port + starboard transducers
and produces a single merged `ProcessedSSSPing` per matched pair, with:

  * raw u16 power samples converted to dB,
  * transducer altitude above the seabed estimated via First-Bottom-Return
    (FBR) detection, fused across the two sides and stabilised across pings,
  * slant-range correction applied (assuming the seabed is flat locally to
    each ping; altitude is allowed to vary between pings — i.e. non-flat
    seabed across the survey),
  * water-column samples dropped per side,
  * robot pose at ping time snapped from the nearest /blueboat/odom sample.

Note on non-flat seabed: this node performs per-ping altitude tracking
(altitude varies between pings) but assumes the seabed is flat within a
single ping's swath. This is standard SSS practice with single-beam
data; truer across-swath bathymetric correction would require extra
information (DVL, MBES, or a bathymetric prior) that we don't have on
this platform.

Topics
------
Sub  /side_scan_sonar/port/profile       blueboat_interfaces/OmniscanProfile
Sub  /side_scan_sonar/starboard/profile  blueboat_interfaces/OmniscanProfile
Sub  /blueboat/odom                      nav_msgs/Odometry
Pub  ~/processed                         blueboat_interfaces/ProcessedSSSPing
"""

from __future__ import annotations

import math
import threading
from collections import deque
from typing import Deque, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from builtin_interfaces.msg import Time as TimeMsg
from nav_msgs.msg import Odometry

from blueboat_interfaces.msg import OmniscanProfile, ProcessedSSSPing


# ---------------------------------------------------------------------------
# Transducer geometry — measure on the physical BlueBoat and fill in.
# All in meters, expressed in base_link (REP-103: +x forward, +y left = port,
# +z up). The y offsets are positive magnitudes; the port/starboard sign is
# applied in code.
# ---------------------------------------------------------------------------
TRANSDUCER_X_OFFSET_M:        float = 0.0   # TODO: forward offset (probably negative — transducers are aft)
TRANSDUCER_Y_OFFSET_PORT_M:   float = 0.0   # TODO: lateral offset of the port transducer (positive)
TRANSDUCER_Y_OFFSET_STBD_M:   float = 0.0   # TODO: lateral offset of the starboard transducer (positive magnitude)
TRANSDUCER_SUBMERSION_M:      float = 0.0   # TODO: depth of transducers below the waterline (positive)


# ---------------------------------------------------------------------------
# FBR / altitude tracking parameters.
# All callable out as constants here so the first field experiment can tune
# them without touching the rest of the code.
# ---------------------------------------------------------------------------
# Within-ping detection: first sample whose dB rises above the noise floor by
# FBR_THRESHOLD_DELTA_DB and stays there for WITHIN_PING_PERSISTENCE samples.
NOISE_FLOOR_WINDOW:       int   = 20    # samples at the start of a ping used to estimate water-column noise
FBR_THRESHOLD_DELTA_DB:   float = 8.0   # dB above the noise floor
WITHIN_PING_PERSISTENCE:  int   = 3     # consecutive samples needed above threshold

# Cross-ping bootstrap: need this many consecutive successful detections that
# agree within ALTITUDE_AGREEMENT_TOL_M before we start publishing. Once
# bootstrapped, every successful FBR updates the altitude; failed detections
# fall back to the last known value.
BOOTSTRAP_PINGS:          int   = 10
ALTITUDE_AGREEMENT_TOL_M: float = 0.30  # max spread (max-min) across bootstrap window

# Time matcher tolerance for pairing port + starboard pings.
TIME_MATCH_TOLERANCE_NS:  int   = 50_000_000  # 50 ms

# Odom buffer length.
ODOM_BUFFER_SECONDS:      float = 5.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _stamp_to_ns(stamp: TimeMsg) -> int:
    return stamp.sec * 1_000_000_000 + stamp.nanosec


def _scale_to_db(pwr_u16, min_pwr_db: float, max_pwr_db: float) -> List[float]:
    """Convert raw u16 power samples to dB.

    Formula from bluerobotics-ping's Omniscan450 template:
      db = min_pwr_db + (raw / 65535) * (max_pwr_db - min_pwr_db)
    https://github.com/bluerobotics/ping-python/blob/master/generate/templates/omniscan450.py.in
    """
    span = max_pwr_db - min_pwr_db
    return [min_pwr_db + (s / 65535.0) * span for s in pwr_u16]


def _detect_fbr_slant_m(
    pwr_db: List[float],
    start_mm: int,
    length_mm: int,
    num_results: int,
) -> Optional[float]:
    """Return the slant range (meters) of the first bottom return, or None.

    Algorithm:
      1. Estimate the water-column noise floor as the mean dB of the first
         NOISE_FLOOR_WINDOW samples.
      2. Set the detection threshold to noise + FBR_THRESHOLD_DELTA_DB.
      3. Find the first index i such that samples i .. i + WITHIN_PING_PERSISTENCE - 1
         are all above the threshold.
      4. Convert i to a slant range using the ping's start_mm + length_mm range.
    """
    n = len(pwr_db)
    if n < NOISE_FLOOR_WINDOW + WITHIN_PING_PERSISTENCE:
        return None
    noise = sum(pwr_db[:NOISE_FLOOR_WINDOW]) / NOISE_FLOOR_WINDOW
    threshold = noise + FBR_THRESHOLD_DELTA_DB
    denom = max(num_results - 1, 1)
    for i in range(NOISE_FLOOR_WINDOW, n - WITHIN_PING_PERSISTENCE + 1):
        # Cheap early-out before the all() check.
        if pwr_db[i] <= threshold:
            continue
        if all(pwr_db[i + k] > threshold for k in range(WITHIN_PING_PERSISTENCE)):
            slant_mm = start_mm + (i / denom) * length_mm
            return slant_mm / 1000.0
    return None


def _project_side(
    pwr_db: List[float],
    start_mm: int,
    length_mm: int,
    num_results: int,
    altitude_m: float,
    transducer_y_offset_m: float,
    side_sign: float,
) -> Tuple[List[float], List[float]]:
    """Slant-range correct one side and drop water-column samples.

    Returns (y_coords_in_base_link, intensities_db) — same length, sample i
    of one is the y / dB of the i-th post-correction sample.

    side_sign = +1 for port, -1 for starboard.
    """
    y_out: List[float] = []
    db_out: List[float] = []
    start_m = start_mm / 1000.0
    length_m = length_mm / 1000.0
    denom = max(num_results - 1, 1)
    # Iterate over the actual number of samples we received.
    n = len(pwr_db)
    for i in range(n):
        slant = start_m + (i / denom) * length_m
        if slant <= altitude_m:
            continue  # water column
        ground = math.sqrt(slant * slant - altitude_m * altitude_m)
        y_out.append(float(side_sign * (transducer_y_offset_m + ground)))
        db_out.append(float(pwr_db[i]))
    return y_out, db_out


# ---------------------------------------------------------------------------
# Odom buffer
# ---------------------------------------------------------------------------
class _OdomBuffer:
    """Thread-safe sliding buffer of recent /blueboat/odom samples.

    Supports nearest-stamp lookup. A linear scan is fine here: at 20 Hz odom
    and a 5 s window the buffer holds ~100 entries.
    """

    def __init__(self, max_age_ns: int):
        self._max_age_ns = max_age_ns
        self._samples: Deque[Tuple[int, Odometry]] = deque()
        self._lock = threading.Lock()

    def push(self, msg: Odometry) -> None:
        ts = _stamp_to_ns(msg.header.stamp)
        with self._lock:
            self._samples.append((ts, msg))
            cutoff = ts - self._max_age_ns
            while self._samples and self._samples[0][0] < cutoff:
                self._samples.popleft()

    def has_data(self) -> bool:
        with self._lock:
            return bool(self._samples)

    def nearest(self, target_ns: int) -> Optional[Odometry]:
        with self._lock:
            if not self._samples:
                return None
            best_ts, best_msg = self._samples[0]
            best_dt = abs(best_ts - target_ns)
            for ts, msg in self._samples:
                dt = abs(ts - target_ns)
                if dt < best_dt:
                    best_ts, best_msg, best_dt = ts, msg, dt
            return best_msg


# ---------------------------------------------------------------------------
# Altitude tracker (FBR + bootstrap + last-known fallback)
# ---------------------------------------------------------------------------
class _FBRTracker:
    """Cross-ping altitude estimator.

    Per-ping inputs are the FBR slant ranges from port and starboard. They
    are fused with max(port, stbd) so that we never under-estimate the
    seabed depth (which would create false 'holes' in the study area, per
    the project's spec).

    Bootstrap: hold off publishing until BOOTSTRAP_PINGS consecutive ping
    pairs produce an estimate AND those estimates span ≤ ALTITUDE_AGREEMENT_TOL_M.
    The bootstrap altitude is the mean of those BOOTSTRAP_PINGS estimates.

    Operational: a successful per-ping estimate replaces the current
    altitude. A failed detection (no FBR on either side) keeps the last
    known value.
    """

    def __init__(self) -> None:
        # maxlen = BOOTSTRAP_PINGS turns this into a sliding window — once the
        # earliest entry falls out, the new entry takes its place, so we
        # naturally retry bootstrap with the most recent N estimates.
        self._bootstrap_window: Deque[float] = deque(maxlen=BOOTSTRAP_PINGS)
        self._altitude: Optional[float] = None  # None until bootstrapped

    @property
    def is_bootstrapped(self) -> bool:
        return self._altitude is not None

    @property
    def altitude(self) -> Optional[float]:
        return self._altitude

    def update(
        self, port_alt: Optional[float], stbd_alt: Optional[float]
    ) -> Optional[float]:
        """Feed one ping pair's FBR results. Returns the current valid altitude
        (or None during bootstrap)."""

        # Fuse the two sides.
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
                # A failed ping breaks the run — clear the window and start over.
                self._bootstrap_window.clear()
                return None
            self._bootstrap_window.append(candidate)
            if len(self._bootstrap_window) == BOOTSTRAP_PINGS:
                spread = max(self._bootstrap_window) - min(self._bootstrap_window)
                if spread <= ALTITUDE_AGREEMENT_TOL_M:
                    self._altitude = sum(self._bootstrap_window) / BOOTSTRAP_PINGS
                # else: sliding window absorbs the next ping and we retry.
            return self._altitude
        else:
            # Operational phase: update if available, otherwise keep last.
            if candidate is not None:
                self._altitude = candidate
            return self._altitude


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------
class SSSProcessorNode(Node):
    """Process raw OmniscanProfile streams into merged ProcessedSSSPing."""

    def __init__(self) -> None:
        super().__init__("sss_processor")

        # ---- Parameters (topics only; geometry is class constants) ---------
        self.declare_parameter("port_topic", "/side_scan_sonar/port/profile")
        self.declare_parameter("starboard_topic", "/side_scan_sonar/starboard/profile")
        self.declare_parameter("odom_topic", "/blueboat/odom")
        self.declare_parameter("processed_topic", "~/processed")

        port_topic = self._str_param("port_topic")
        stbd_topic = self._str_param("starboard_topic")
        odom_topic = self._str_param("odom_topic")
        processed_topic = self._str_param("processed_topic")

        # ---- State ---------------------------------------------------------
        self._port_buf: Deque[OmniscanProfile] = deque()
        self._stbd_buf: Deque[OmniscanProfile] = deque()
        self._buf_lock = threading.Lock()
        self._tol_ns = TIME_MATCH_TOLERANCE_NS

        self._odom_buf = _OdomBuffer(int(ODOM_BUFFER_SECONDS * 1e9))
        self._fbr = _FBRTracker()

        # Drop counters (for sparing logs).
        self._dropped_no_odom = 0
        self._dropped_bootstrap = 0
        self._already_bootstrapped_logged = False

        # ---- QoS -----------------------------------------------------------
        sonar_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        odom_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )

        # ---- IO ------------------------------------------------------------
        self.create_subscription(OmniscanProfile, port_topic, self._on_port, sonar_qos)
        self.create_subscription(OmniscanProfile, stbd_topic, self._on_starboard, sonar_qos)
        self.create_subscription(Odometry, odom_topic, self._on_odom, odom_qos)
        self._pub = self.create_publisher(ProcessedSSSPing, processed_topic, sonar_qos)

        self.get_logger().info(
            "sss_processor ready:\n"
            f"  port  ← {port_topic}\n"
            f"  stbd  ← {stbd_topic}\n"
            f"  odom  ← {odom_topic}\n"
            f"  out   → {processed_topic}\n"
            f"  bootstrap: {BOOTSTRAP_PINGS} ping pairs within "
            f"{ALTITUDE_AGREEMENT_TOL_M*100:.0f} cm"
        )

    # ----- subscribers ------------------------------------------------------
    def _on_port(self, msg: OmniscanProfile) -> None:
        with self._buf_lock:
            self._port_buf.append(msg)
            self._drain_matches()

    def _on_starboard(self, msg: OmniscanProfile) -> None:
        with self._buf_lock:
            self._stbd_buf.append(msg)
            self._drain_matches()

    def _on_odom(self, msg: Odometry) -> None:
        self._odom_buf.push(msg)

    # ----- two-pointer time matcher -----------------------------------------
    def _drain_matches(self) -> None:
        """Emit every possible match from the head of both buffers.
        Called under self._buf_lock. Standard two-pointer merge: if the
        oldest port and oldest starboard are within tolerance, match;
        otherwise drop whichever is older (it's never going to find a
        partner).
        """
        while self._port_buf and self._stbd_buf:
            p = self._port_buf[0]
            s = self._stbd_buf[0]
            p_ns = _stamp_to_ns(p.header.stamp)
            s_ns = _stamp_to_ns(s.header.stamp)
            dt = p_ns - s_ns
            if abs(dt) <= self._tol_ns:
                self._port_buf.popleft()
                self._stbd_buf.popleft()
                self._emit_merged(p, s)
            elif dt > 0:
                # Port is newer; starboard at head has no chance of matching.
                self._stbd_buf.popleft()
            else:
                # Starboard is newer; port at head has no chance.
                self._port_buf.popleft()

    # ----- processing -------------------------------------------------------
    def _emit_merged(self, port: OmniscanProfile, stbd: OmniscanProfile) -> None:
        log = self.get_logger()

        # 1. Odom must exist; if SSS started before robot_interface, drop early pings.
        if not self._odom_buf.has_data():
            self._dropped_no_odom += 1
            if self._dropped_no_odom == 1 or self._dropped_no_odom % 20 == 0:
                log.warn(
                    f"dropping ping pair: no /blueboat/odom yet "
                    f"(total dropped: {self._dropped_no_odom})"
                )
            return

        # 2. dB conversion.
        port_db = _scale_to_db(port.pwr_results, port.min_pwr_db, port.max_pwr_db)
        stbd_db = _scale_to_db(stbd.pwr_results, stbd.min_pwr_db, stbd.max_pwr_db)

        # 3. FBR detection per side.
        port_alt = _detect_fbr_slant_m(port_db, port.start_mm, port.length_mm, port.num_results)
        stbd_alt = _detect_fbr_slant_m(stbd_db, stbd.start_mm, stbd.length_mm, stbd.num_results)

        # 4. Update the cross-ping altitude tracker.
        altitude = self._fbr.update(port_alt, stbd_alt)
        if altitude is None:
            self._dropped_bootstrap += 1
            if self._dropped_bootstrap == 1 or self._dropped_bootstrap % BOOTSTRAP_PINGS == 0:
                log.info(
                    f"FBR bootstrap in progress "
                    f"({self._dropped_bootstrap} ping pairs dropped so far; "
                    f"port_fbr={port_alt}, stbd_fbr={stbd_alt})"
                )
            return
        if not self._already_bootstrapped_logged:
            log.info(f"FBR bootstrapped: altitude = {altitude:.2f} m above seabed")
            self._already_bootstrapped_logged = True

        # 5. Water depth = transducer altitude above seabed + transducer submersion.
        water_depth = altitude + TRANSDUCER_SUBMERSION_M

        # 6. Slant-range correct each side; drop water-column samples.
        port_y, port_int = _project_side(
            port_db, port.start_mm, port.length_mm, port.num_results,
            altitude_m=altitude,
            transducer_y_offset_m=TRANSDUCER_Y_OFFSET_PORT_M,
            side_sign=+1.0,
        )
        stbd_y, stbd_int = _project_side(
            stbd_db, stbd.start_mm, stbd.length_mm, stbd.num_results,
            altitude_m=altitude,
            transducer_y_offset_m=TRANSDUCER_Y_OFFSET_STBD_M,
            side_sign=-1.0,
        )

        # 7. Snap robot pose: use port stamp as the merged-pair reference
        #    (port and stbd are within TIME_MATCH_TOLERANCE_NS by construction).
        merged_ns = _stamp_to_ns(port.header.stamp)
        odom = self._odom_buf.nearest(merged_ns)
        if odom is None:
            # Should be impossible given the has_data() check above, but be safe.
            self._dropped_no_odom += 1
            return

        # 8. Assemble + publish.
        out = ProcessedSSSPing()

        out.port_stamp = port.header.stamp
        out.starboard_stamp = stbd.header.stamp
        out.port_ping_number = port.ping_number
        out.starboard_ping_number = stbd.ping_number

        out.robot_x = float(odom.pose.pose.position.x)
        out.robot_y = float(odom.pose.pose.position.y)
        out.robot_orientation = odom.pose.pose.orientation

        out.water_depth = float(water_depth)
        out.transducer_x_offset = float(TRANSDUCER_X_OFFSET_M)

        out.port_intensity_db = port_int
        out.port_y = port_y
        out.starboard_intensity_db = stbd_int
        out.starboard_y = stbd_y

        self._pub.publish(out)

    # ----- helpers ----------------------------------------------------------
    def _str_param(self, name: str) -> str:
        return self.get_parameter(name).get_parameter_value().string_value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(args=None) -> None:
    rclpy.init(args=args)
    node = SSSProcessorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
