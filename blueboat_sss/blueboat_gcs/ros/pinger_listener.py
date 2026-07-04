"""USBL pinger position listener — **PLACEHOLDER / INTEGRATION POINT**.

The USBL localisation stack lives in the robot-control repositories and
is not available here. The GUI side (PingerLayer marker + visibility
toggle) is fully implemented; this listener is where the real topic gets
plugged in.

Expected interface (adjust the three constants + `_msg_to_fix` only):

    Topic   : config ``topics.pinger`` (default /usbl/pinger/position)
    Type    : geometry_msgs/PointStamped
              point.x / point.y = pinger position in the *local odom
              frame* (same frame as /blueboat/odom, metres); point.z is
              ignored by the GUI (depth, free for future use).
    Rate    : 1–5 Hz (whatever the USBL produces; the GUI keeps only the
              last fix, so any rate works).

If the USBL stack publishes a different type (e.g.
geometry_msgs/PoseWithCovarianceStamped, or a NavSatFix in WGS-84),
change the import + `_msg_to_fix`; for GPS input, convert via the
CoordinateConverter in main_window instead of here (keep listeners
frame-agnostic is also fine — pick one and document it).
"""

from __future__ import annotations

from geometry_msgs.msg import PointStamped
from rclpy.node import Node

from ..core.signals import AppSignals
from ..models.detection import PingerFix

# Accuracy is not part of PointStamped; keep a conservative default ring.
# Replace with the covariance if you switch to PoseWithCovarianceStamped.
DEFAULT_ACCURACY_M = 2.0


class PingerListener:
    """Forwards the last known USBL pinger fix to the GUI."""

    def __init__(self, node: Node, signals: AppSignals, topic: str) -> None:
        self._signals = signals
        node.create_subscription(PointStamped, topic, self._on_msg, 10)

    def _on_msg(self, msg: PointStamped) -> None:
        self._signals.pinger_fix.emit(self._msg_to_fix(msg))

    @staticmethod
    def _msg_to_fix(msg: PointStamped) -> PingerFix:
        """<-- EDIT HERE when connecting the real USBL topic."""
        return PingerFix(
            t=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
            x=float(msg.point.x),
            y=float(msg.point.y),
            accuracy_m=DEFAULT_ACCURACY_M,
        )
