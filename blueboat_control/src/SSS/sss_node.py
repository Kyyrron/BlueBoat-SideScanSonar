#!/usr/bin/env python3
"""
Side Scan Sonar (SSS) ROS 2 node for the BlueBoat.

Drives the pair of Cerulean Omniscan 450 SS devices (port + starboard) and
republishes their `os_mono_profile` packets on two ROS topics, in two forms:

  * parsed `OmniscanProfile` -- for downstream processing,
  * raw framed Ping-Protocol bytes (`UInt8MultiArray`) -- for the processor
    node to interleave into a SonarView .svlog file.

Pinging is OFF when the node starts. Connections are opened immediately so
the devices are ready to fire on demand. On-disk logging is no longer this
node's responsibility -- the processor node owns the .svlog file.

Topics
------
Pub  ~/port/profile         blueboat_interfaces/OmniscanProfile
Pub  ~/port/raw             std_msgs/UInt8MultiArray
Pub  ~/starboard/profile    blueboat_interfaces/OmniscanProfile
Pub  ~/starboard/raw        std_msgs/UInt8MultiArray
Sub  ~/ping/enable          std_msgs/Bool   true=start, false=stop

Run-dependent parameters
------------------------
Network        port_ip, port_tcp_port, starboard_ip, starboard_tcp_port
Acquisition    range_start_mm, range_length_mm, msec_per_ping, gain_index,
               num_results, pulse_len_percent
Frames         port_frame_id, starboard_frame_id

Acquisition parameters are re-read each time pinging is enabled, so
`ros2 param set ...` between runs takes effect on the next "start".
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool, UInt8MultiArray

# bluerobotics-ping -- pip install --user bluerobotics-ping --upgrade
from brping import Omniscan450, definitions

from blueboat_interfaces.msg import OmniscanProfile


# ---------------------------------------------------------------------------
# Pinned (non run-dependent) parameters
# ---------------------------------------------------------------------------
FILTER_DURATION_PERCENT: float = 0.0015     # Cerulean docs: 0.0015 typical
WORKER_JOIN_TIMEOUT_S:   float = 3.0


@dataclass(frozen=True)
class PingParams:
    """Run-dependent ping configuration shared by both transducers."""

    start_mm: int
    length_mm: int
    msec_per_ping: int
    gain_index: int
    num_results: int
    pulse_len_percent: float


# ---------------------------------------------------------------------------
# Per-device worker
# ---------------------------------------------------------------------------
class OmniscanWorker:
    """Owns one Omniscan450. Publishes parsed + raw packets for one side."""

    def __init__(
        self,
        node: Node,
        side: str,
        ip: str,
        tcp_port: int,
        profile_publisher,
        raw_publisher,
        frame_id: str,
    ) -> None:
        self._node = node
        self._side = side
        self._ip = ip
        self._tcp_port = tcp_port
        self._profile_pub = profile_publisher
        self._raw_pub = raw_publisher
        self._frame_id = frame_id

        self._device: Optional[Omniscan450] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._control_lock = threading.Lock()
        self._pinging = False

    # ----- lifecycle -------------------------------------------------------
    def start(self) -> bool:
        log = self._node.get_logger()
        # logging=False -- on-disk logging is the processor node's job.
        self._device = Omniscan450(logging=False)
        log.info(
            f"[{self._side}] connecting to Omniscan450 at "
            f"{self._ip}:{self._tcp_port} (TCP)"
        )
        try:
            self._device.connect_tcp(self._ip, self._tcp_port)
        except Exception as exc:  # noqa: BLE001
            log.error(f"[{self._side}] TCP connect failed: {exc}")
            return False

        if self._device.initialize() is False:
            log.error(f"[{self._side}] Omniscan450.initialize() returned False")
            return False

        try:
            self._device.control_os_ping_params(enable=0)
        except Exception:  # noqa: BLE001
            pass

        self._running.set()
        self._thread = threading.Thread(
            target=self._spin, name=f"omniscan-{self._side}", daemon=True
        )
        self._thread.start()
        log.info(f"[{self._side}] connected, idle (ping OFF)")
        return True

    def stop(self) -> None:
        try:
            self.set_pinging(False)
        except Exception:  # noqa: BLE001
            pass
        self._running.clear()
        if self._thread is not None:
            self._thread.join(timeout=WORKER_JOIN_TIMEOUT_S)
        if self._device is not None:
            try:
                if self._device.iodev:
                    self._device.iodev.close()
            except Exception:  # noqa: BLE001
                pass

    # ----- control ---------------------------------------------------------
    def set_pinging(self, enable: bool, params: Optional[PingParams] = None) -> bool:
        log = self._node.get_logger()
        with self._control_lock:
            if self._device is None:
                return False
            if enable == self._pinging:
                return True
            try:
                if enable:
                    if params is None:
                        log.error(f"[{self._side}] cannot start ping without params")
                        return False
                    self._device.control_os_ping_params(
                        start_mm=params.start_mm,
                        length_mm=params.length_mm,
                        msec_per_ping=params.msec_per_ping,
                        pulse_len_percent=params.pulse_len_percent,
                        filter_duration_percent=FILTER_DURATION_PERCENT,
                        gain_index=params.gain_index,
                        num_results=params.num_results,
                        enable=1,
                    )
                    log.info(
                        f"[{self._side}] pinging started "
                        f"(range {params.start_mm}-{params.start_mm + params.length_mm} mm, "
                        f"gain {params.gain_index}, n={params.num_results})"
                    )
                else:
                    self._device.control_os_ping_params(enable=0)
                    log.info(f"[{self._side}] pinging stopped")
            except Exception as exc:  # noqa: BLE001
                log.error(f"[{self._side}] set_pinging({enable}) failed: {exc}")
                return False
            self._pinging = enable
            return True

    # ----- internals -------------------------------------------------------
    def _spin(self) -> None:
        log = self._node.get_logger()
        target = [definitions.OMNISCAN450_OS_MONO_PROFILE]
        while self._running.is_set() and rclpy.ok():
            try:
                data = self._device.wait_message(target)
            except Exception as exc:  # noqa: BLE001
                log.warn(f"[{self._side}] wait_message error: {exc}")
                continue
            if data is None:
                continue
            self._publish_profile(data)
            # brping populates msg_data inside wait_message with the
            # already-framed Ping-Protocol bytes -- republish verbatim.
            if data.msg_data:
                self._publish_raw(bytes(data.msg_data))

    def _publish_profile(self, data) -> None:
        msg = OmniscanProfile()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.side = self._side

        msg.ping_number = int(data.ping_number)
        msg.start_mm = int(data.start_mm)
        msg.length_mm = int(data.length_mm)
        msg.timestamp_ms = int(data.timestamp_ms)
        msg.ping_hz = int(data.ping_hz)
        msg.gain_index = int(data.gain_index)
        msg.num_results = int(data.num_results)
        msg.sos_dmps = int(data.sos_dmps)
        msg.channel_number = int(data.channel_number)
        msg.pulse_duration_sec = float(data.pulse_duration_sec)
        msg.analog_gain = float(data.analog_gain)
        msg.max_pwr_db = float(data.max_pwr_db)
        msg.min_pwr_db = float(data.min_pwr_db)
        msg.transducer_heading_deg = float(data.transducer_heading_deg)
        msg.vehicle_heading_deg = float(data.vehicle_heading_deg)
        msg.pwr_results = list(data.pwr_results)

        self._profile_pub.publish(msg)

    def _publish_raw(self, raw: bytes) -> None:
        msg = UInt8MultiArray()
        # rclpy expects a sequence of ints for uint8[] fields; list(bytes)
        # is unambiguous and avoids any binding-version pitfalls.
        msg.data = list(raw)
        self._raw_pub.publish(msg)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------
class SideScanSonarNode(Node):
    """ROS 2 node managing the port + starboard Omniscan 450 SS devices."""

    def __init__(self) -> None:
        super().__init__("side_scan_sonar")

        # ---- Run-dependent parameters --------------------------------------
        self.declare_parameter("port_ip", "192.168.2.92")
        self.declare_parameter("port_tcp_port", 51200)
        self.declare_parameter("starboard_ip", "192.168.2.93")
        self.declare_parameter("starboard_tcp_port", 51200)

        self.declare_parameter("range_start_mm", 0)
        self.declare_parameter("range_length_mm", 30000)
        self.declare_parameter("msec_per_ping", 0)
        self.declare_parameter("gain_index", -1)
        self.declare_parameter("num_results", 600)
        self.declare_parameter("pulse_len_percent", 0.002)

        self.declare_parameter("port_frame_id", "sss_port_link")
        self.declare_parameter("starboard_frame_id", "sss_starboard_link")

        # ---- Publishers (best-effort: sonar is a high-rate lossy stream) ---
        sonar_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._port_profile_pub = self.create_publisher(
            OmniscanProfile, "~/port/profile", sonar_qos
        )
        self._port_raw_pub = self.create_publisher(
            UInt8MultiArray, "~/port/raw", sonar_qos
        )
        self._stbd_profile_pub = self.create_publisher(
            OmniscanProfile, "~/starboard/profile", sonar_qos
        )
        self._stbd_raw_pub = self.create_publisher(
            UInt8MultiArray, "~/starboard/raw", sonar_qos
        )

        # ---- Workers --------------------------------------------------------
        self._port_worker = OmniscanWorker(
            self,
            side="port",
            ip=self._str_param("port_ip"),
            tcp_port=self._int_param("port_tcp_port"),
            profile_publisher=self._port_profile_pub,
            raw_publisher=self._port_raw_pub,
            frame_id=self._str_param("port_frame_id"),
        )
        self._starboard_worker = OmniscanWorker(
            self,
            side="starboard",
            ip=self._str_param("starboard_ip"),
            tcp_port=self._int_param("starboard_tcp_port"),
            profile_publisher=self._stbd_profile_pub,
            raw_publisher=self._stbd_raw_pub,
            frame_id=self._str_param("starboard_frame_id"),
        )

        if not self._port_worker.start():
            self.get_logger().error("port-side Omniscan failed to start")
        if not self._starboard_worker.start():
            self.get_logger().error("starboard-side Omniscan failed to start")

        # ---- Control subscriber --------------------------------------------
        self.create_subscription(Bool, "~/ping/enable", self._on_ping_enable, 10)

        self.get_logger().info(
            "side_scan_sonar ready, ping OFF. Toggle with:\n"
            "  ros2 topic pub --once /side_scan_sonar/ping/enable std_msgs/msg/Bool 'data: true'"
        )

    # ----- callbacks --------------------------------------------------------
    def _on_ping_enable(self, msg: Bool) -> None:
        if msg.data:
            params = self._collect_ping_params()
            self._port_worker.set_pinging(True, params)
            self._starboard_worker.set_pinging(True, params)
        else:
            self._port_worker.set_pinging(False)
            self._starboard_worker.set_pinging(False)

    # ----- shutdown ---------------------------------------------------------
    def shutdown(self) -> None:
        self.get_logger().info("stopping side scan sonar node")
        self._port_worker.stop()
        self._starboard_worker.stop()

    # ----- helpers ----------------------------------------------------------
    def _collect_ping_params(self) -> PingParams:
        return PingParams(
            start_mm=self._int_param("range_start_mm"),
            length_mm=self._int_param("range_length_mm"),
            msec_per_ping=self._int_param("msec_per_ping"),
            gain_index=self._int_param("gain_index"),
            num_results=self._int_param("num_results"),
            pulse_len_percent=self._float_param("pulse_len_percent"),
        )

    def _str_param(self, name: str) -> str:
        return self.get_parameter(name).get_parameter_value().string_value

    def _int_param(self, name: str) -> int:
        return self.get_parameter(name).get_parameter_value().integer_value

    def _float_param(self, name: str) -> float:
        return self.get_parameter(name).get_parameter_value().double_value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main(args=None) -> None:
    rclpy.init(args=args)
    node = SideScanSonarNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
