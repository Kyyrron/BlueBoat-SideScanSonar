#!/usr/bin/env python3
"""
Side Scan Sonar (SSS) ROS 2 node for the BlueBoat.

Drives the pair of Cerulean Omniscan 450 SS devices (port + starboard),
republishes raw `os_mono_profile` packets, and accepts run-time toggles
to start/stop pinging and start/stop on-disk logging.

Pinging and logging are BOTH OFF when the node starts. Connections are
opened immediately so the device is ready to fire on demand.

Topics
------
Pub  ~/port/profile         blueboat_interfaces/OmniscanProfile
Pub  ~/starboard/profile    blueboat_interfaces/OmniscanProfile
Sub  ~/ping/enable          std_msgs/Bool   true=start, false=stop
Sub  ~/log/enable           std_msgs/Bool   true=start, false=stop

Run-dependent parameters
------------------------
Network        port_ip, port_tcp_port, starboard_ip, starboard_tcp_port
Acquisition    range_start_mm, range_length_mm, msec_per_ping, gain_index,
               num_results, pulse_len_percent
Logging        log_directory  (created if missing; per-side subdirs are
                               appended automatically)
Frames         port_frame_id, starboard_frame_id

The acquisition parameters are re-read each time pinging is enabled, so
`ros2 param set ...` between runs takes effect on the next "start".
"""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool

# bluerobotics-ping -- install with:  pip install --user bluerobotics-ping --upgrade
from brping import Omniscan450, definitions

from blueboat_interfaces.msg import OmniscanProfile


# ---------------------------------------------------------------------------
# Pinned (non run-dependent) parameters
# ---------------------------------------------------------------------------
FILTER_DURATION_PERCENT: float = 0.0015     # Cerulean docs: 0.0015 typical
WORKER_JOIN_TIMEOUT_S: float = 3.0


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
    """Owns one Omniscan450 device. Thread receives, lock guards control."""

    def __init__(
        self,
        node: Node,
        side: str,
        ip: str,
        tcp_port: int,
        publisher,
        frame_id: str,
        log_dir: Path,
    ) -> None:
        self._node = node
        self._side = side
        self._ip = ip
        self._tcp_port = tcp_port
        self._publisher = publisher
        self._frame_id = frame_id
        self._log_dir = log_dir

        self._device: Optional[Omniscan450] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self._pinging = False
        self._logging = False

    # ----- lifecycle -------------------------------------------------------
    def start(self) -> bool:
        """Connect to the device and start the receive thread; pinging stays OFF."""
        log = self._node.get_logger()

        try:
            self._log_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.error(f"[{self._side}] cannot create log dir {self._log_dir}: {exc}")
            return False

        # logging=True only enables the *capability* -- writing only happens
        # between start_logging() and stop_logging() on the device.
        self._device = Omniscan450(logging=True, log_directory=str(self._log_dir))

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

        # Start in a known clean state on the device side too.
        try:
            self._device.control_os_ping_params(enable=0)
        except Exception:  # noqa: BLE001
            pass

        self._running.set()
        self._thread = threading.Thread(
            target=self._spin, name=f"omniscan-{self._side}", daemon=True
        )
        self._thread.start()
        log.info(f"[{self._side}] connected, idle (ping OFF, log OFF)")
        return True

    def stop(self) -> None:
        # Stop logging first, then pinging, then drain the thread.
        try:
            self.set_logging(False)
        except Exception:  # noqa: BLE001
            pass
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
        """Toggle pinging. `params` is required when enabling."""
        log = self._node.get_logger()
        with self._lock:
            if self._device is None:
                return False
            if enable == self._pinging:
                return True  # idempotent

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

    def set_logging(self, enable: bool) -> bool:
        log = self._node.get_logger()
        with self._lock:
            if self._device is None:
                return False
            if enable == self._logging:
                return True  # idempotent

            try:
                if enable:
                    # new_log=True rolls a fresh .svlog file each time we
                    # transition off->on, instead of appending to the
                    # previous one. Easier to keep recordings tidy.
                    self._device.start_logging(new_log=True)
                    log.info(f"[{self._side}] logging -> {self._log_dir}")
                else:
                    self._device.stop_logging()
                    log.info(f"[{self._side}] logging stopped")
            except Exception as exc:  # noqa: BLE001
                log.error(f"[{self._side}] set_logging({enable}) failed: {exc}")
                return False

            self._logging = enable
            return True

    # ----- internals -------------------------------------------------------
    def _spin(self) -> None:
        log = self._node.get_logger()
        target = [definitions.OMNISCAN450_OS_MONO_PROFILE]

        # When pinging is disabled the device sends nothing; wait_message()
        # returns None on its internal timeout and we just loop again.
        while self._running.is_set() and rclpy.ok():
            try:
                data = self._device.wait_message(target)
            except Exception as exc:  # noqa: BLE001
                log.warn(f"[{self._side}] wait_message error: {exc}")
                continue
            if data is None:
                continue
            self._publish(data)

    def _publish(self, data) -> None:
        msg = OmniscanProfile()
        msg.header.stamp = self._node.get_clock().now().to_msg()
        msg.header.frame_id = self._frame_id
        msg.side = self._side

        # Straight passthrough -- no preprocessing applied.
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

        self._publisher.publish(msg)


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------
class SideScanSonarNode(Node):
    """ROS 2 node managing the port + starboard Omniscan 450 SS devices."""

    def __init__(self) -> None:
        super().__init__("sss_node")

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

        self.declare_parameter("log_directory", "~/sss_logs")

        self.declare_parameter("port_frame_id", "sss_port_link")
        self.declare_parameter("starboard_frame_id", "sss_starboard_link")

        # ---- Publishers (best-effort, sonar is a high-rate lossy stream) ---
        sonar_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        self._port_pub = self.create_publisher(
            OmniscanProfile, "~/port/profile", sonar_qos
        )
        self._starboard_pub = self.create_publisher(
            OmniscanProfile, "~/starboard/profile", sonar_qos
        )

        # ---- Workers --------------------------------------------------------
        log_root = Path(os.path.expanduser(self._str_param("log_directory")))
        self.get_logger().info(f"log root: {log_root}")

        self._port_worker = OmniscanWorker(
            self,
            side="port",
            ip=self._str_param("port_ip"),
            tcp_port=self._int_param("port_tcp_port"),
            publisher=self._port_pub,
            frame_id=self._str_param("port_frame_id"),
            log_dir=log_root / "port",
        )
        self._starboard_worker = OmniscanWorker(
            self,
            side="starboard",
            ip=self._str_param("starboard_ip"),
            tcp_port=self._int_param("starboard_tcp_port"),
            publisher=self._starboard_pub,
            frame_id=self._str_param("starboard_frame_id"),
            log_dir=log_root / "starboard",
        )

        if not self._port_worker.start():
            self.get_logger().error("port-side Omniscan failed to start")
        if not self._starboard_worker.start():
            self.get_logger().error("starboard-side Omniscan failed to start")

        # ---- Control subscribers -------------------------------------------
        # Default QoS (reliable, depth 10) -- ros2 topic pub --once works fine.
        self.create_subscription(Bool, "~/ping/enable", self._on_ping_enable, 10)
        self.create_subscription(Bool, "~/log/enable", self._on_log_enable, 10)

        self.get_logger().info(
            "sss_node ready, ping OFF, log OFF. Toggle with:\n"
            "  ros2 topic pub --once /sss_node/ping/enable std_msgs/msg/Bool 'data: true'\n"
            "  ros2 topic pub --once /sss_node/log/enable  std_msgs/msg/Bool 'data: true'"
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

    def _on_log_enable(self, msg: Bool) -> None:
        self._port_worker.set_logging(msg.data)
        self._starboard_worker.set_logging(msg.data)

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
