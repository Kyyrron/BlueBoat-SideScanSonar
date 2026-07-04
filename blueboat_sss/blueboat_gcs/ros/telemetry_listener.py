"""Robot telemetry aggregation.

Topics (all provided by the robot-control repositories; mavros + odom):

======================================  ==========================  ======
Topic (config key)                      Message type                Rate
======================================  ==========================  ======
topics.odom                             nav_msgs/Odometry           ~20 Hz
topics.navsat                           sensor_msgs/NavSatFix       ~5 Hz
topics.compass_hdg                      std_msgs/Float64 (degrees)  ~10 Hz
topics.vfr_hud (optional)               mavros_msgs/VfrHud          ~4 Hz
======================================  ==========================  ======

The listener merges the latest values into a ``RobotState`` and emits it
on every odom message, throttled to ``EMIT_HZ`` — the panels do not need
20 Hz updates, and this keeps the queued-signal traffic low.

The GUI-side ``CoordinateConverter`` binds its GPS origin from the first
RobotState that carries both a local pose and a fix (see main_window).
mavros_msgs is optional: without it, speed falls back to the odom twist.
"""

from __future__ import annotations

import math
import threading
from typing import Optional

from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import NavSatFix
from std_msgs.msg import Float64

from ..config.settings import RosTopics
from ..core.signals import AppSignals
from ..models.robot_state import RobotState
from ..utils.geodesy import quat_to_yaw, yaw_to_compass_deg

try:  # pragma: no cover - mavros_msgs may be absent on the basestation
    from mavros_msgs.msg import VfrHud
    MAVROS_MSGS_AVAILABLE = True
except ImportError:  # pragma: no cover
    MAVROS_MSGS_AVAILABLE = False

EMIT_HZ = 5.0


class TelemetryListener:
    """Merges odom + mavros telemetry into RobotState signals."""

    def __init__(self, node: Node, signals: AppSignals,
                 topics: RosTopics) -> None:
        self._signals = signals
        self._lock = threading.Lock()
        self._lat: Optional[float] = None
        self._lon: Optional[float] = None
        self._compass_deg: Optional[float] = None
        self._speed: Optional[float] = None
        self._last_emit_t = 0.0

        best_effort = QoSProfile(reliability=ReliabilityPolicy.BEST_EFFORT,
                                 history=HistoryPolicy.KEEP_LAST, depth=10)
        node.create_subscription(Odometry, topics.odom,
                                 self._on_odom, best_effort)
        node.create_subscription(NavSatFix, topics.navsat,
                                 self._on_navsat, best_effort)
        node.create_subscription(Float64, topics.compass_hdg,
                                 self._on_compass, 10)
        if MAVROS_MSGS_AVAILABLE:
            node.create_subscription(VfrHud, topics.vfr_hud,
                                     self._on_vfr_hud, best_effort)
        else:
            signals.status_message.emit(
                "mavros_msgs not found — speed derived from odom twist.")

    # ---- callbacks (ROS thread) -----------------------------------------------
    def _on_navsat(self, msg: NavSatFix) -> None:
        if (msg.status.status < 0 or math.isnan(msg.latitude)
                or math.isnan(msg.longitude)):
            return
        with self._lock:
            self._lat, self._lon = float(msg.latitude), float(msg.longitude)

    def _on_compass(self, msg: Float64) -> None:
        if math.isnan(msg.data) or math.isinf(msg.data):
            return
        with self._lock:
            self._compass_deg = float(msg.data) % 360.0

    def _on_vfr_hud(self, msg: "VfrHud") -> None:
        with self._lock:
            self._speed = float(msg.groundspeed)

    def _on_odom(self, msg: Odometry) -> None:
        t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if t - self._last_emit_t < 1.0 / EMIT_HZ:
            return
        self._last_emit_t = t
        q = msg.pose.pose.orientation
        yaw = quat_to_yaw(q.x, q.y, q.z, q.w)
        with self._lock:
            lat, lon = self._lat, self._lon
            heading = self._compass_deg
            speed = self._speed
        if heading is None:
            heading = yaw_to_compass_deg(yaw)  # odom frame assumed ENU
        if speed is None:
            tw = msg.twist.twist.linear
            speed = math.hypot(tw.x, tw.y)
        self._signals.robot_state.emit(RobotState(
            t=t,
            x=float(msg.pose.pose.position.x),
            y=float(msg.pose.pose.position.y),
            yaw=yaw, lat=lat, lon=lon,
            heading_deg=heading, speed_mps=speed,
        ))
