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
Logging        log_directory  (created if missing)
Frames         port_frame_id, starboard_frame_id

The acquisition parameters are re-read each time pinging is enabled, so
`ros2 param set ...` between runs takes effect on the next "start".
"""

from __future__ import annotations

import json
import os
import platform
import struct
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

from std_msgs.msg import Bool

# bluerobotics-ping -- install with:  pip install --user bluerobotics-ping --upgrade
from brping import Omniscan450, definitions, pingmessage

from blueboat_interfaces.msg import OmniscanProfile


# ---------------------------------------------------------------------------
# Pinned (non run-dependent) parameters
# ---------------------------------------------------------------------------
FILTER_DURATION_PERCENT: float = 0.0015     # Cerulean docs: 0.0015 typical
WORKER_JOIN_TIMEOUT_S: float = 3.0
MAX_LOG_SIZE_BYTES: int = 500 * 1000 * 1000  # mirrors brping's MAX_LOG_SIZE_MB (500 MB default)


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
# Shared svlog writer -- one file, two channels, SonarView-compatible
# ---------------------------------------------------------------------------
class SvlogWriter:
    """Thread-safe single-file SonarView log writer for two Omniscan devices.

    Mirrors what `brping.Omniscan450.write_data()` does, but for both
    devices at once:
      1. On `start()`, write one JSON metadata packet whose
         `session_devices` lists BOTH transducers.
      2. On every subsequent `write()` call, append the raw packet bytes
         (already framed by the library as 'BR' + len + id + payload +
         checksum). The per-packet `channel_number` field tells SonarView
         which side each packet came from.
      3. On reaching MAX_LOG_SIZE_BYTES, roll to a new file (re-writes
         metadata).
    """

    def __init__(self, log_dir: Path, port_url: str, starboard_url: str) -> None:
        self._log_dir = log_dir
        self._port_url = port_url
        self._starboard_url = starboard_url

        self._lock = threading.Lock()
        self._active = False
        self._path: Optional[Path] = None
        self._bytes_written = 0

    # ----- public API ------------------------------------------------------
    @property
    def active(self) -> bool:
        with self._lock:
            return self._active

    @property
    def current_path(self) -> Optional[Path]:
        with self._lock:
            return self._path

    def start(self) -> Optional[Path]:
        """Open a new .svlog with the dual-device metadata header."""
        with self._lock:
            if self._active:
                return self._path
            self._log_dir.mkdir(parents=True, exist_ok=True)
            self._roll_unlocked()
            self._active = True
            return self._path

    def stop(self) -> None:
        with self._lock:
            self._active = False
            self._path = None
            self._bytes_written = 0

    def write(self, raw_bytes: bytes) -> None:
        """Append one already-framed Ping-Protocol packet."""
        with self._lock:
            if not self._active or self._path is None:
                return
            if self._bytes_written > MAX_LOG_SIZE_BYTES:
                self._roll_unlocked()
            try:
                with open(self._path, "ab") as f:
                    f.write(raw_bytes)
                self._bytes_written += len(raw_bytes)
            except OSError:
                # Disk full / unmounted / permissions -- stop quietly.
                self._active = False
                self._path = None

    # ----- internals -------------------------------------------------------
    def _roll_unlocked(self) -> None:
        """Open a fresh .svlog and write the dual-device metadata packet."""
        save_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        path = self._log_dir / f"{save_name}.svlog"
        if path.exists():
            path.unlink()
        self._path = path
        self._bytes_written = 0

        meta = self._build_dual_metadata_packet()
        with open(path, "ab") as f:
            f.write(meta)
        self._bytes_written += len(meta)

    def _build_dual_metadata_packet(self) -> bytes:
        """SonarView session-header JSON wrapped in a JSON_WRAPPER packet."""
        content = {
            "session_id": 1,
            "session_uptime": 0.0,
            "session_devices": [
                {"url": self._port_url, "product_id": "os450"},
                {"url": self._starboard_url, "product_id": "os450"},
            ],
            "session_platform": None,
            "session_clients": [],
            "session_plan_name": None,
            "is_recording": True,
            "sonarlink_version": "",
            "os_hostname": platform.node(),
            "os_uptime": None,
            "os_version": platform.version(),
            "os_platform": platform.system().lower(),
            "os_release": platform.release(),
            "process_path": sys.executable,
            "process_version": f"v{platform.python_version()}",
            "process_uptime": time.process_time(),
            "process_arch": platform.machine(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "timestamp_timezone_offset":
                datetime.now().astimezone().utcoffset().total_seconds() // 60,
        }

        json_bytes = json.dumps(content, indent=2).encode("utf-8")

        m = pingmessage.PingMessage(definitions.OMNISCAN450_JSON_WRAPPER)
        m.payload = json_bytes
        m.payload_length = len(json_bytes)

        msg_data = bytearray()
        msg_data += b"BR"
        msg_data += m.payload_length.to_bytes(2, "little")
        msg_data += m.message_id.to_bytes(2, "little")
        msg_data += m.dst_device_id.to_bytes(1, "little")
        msg_data += m.src_device_id.to_bytes(1, "little")
        msg_data += m.payload

        checksum = sum(msg_data) & 0xFFFF
        msg_data += bytearray(
            struct.pack(
                pingmessage.PingMessage.endianess
                + pingmessage.PingMessage.checksum_format,
                checksum,
            )
        )
        return bytes(msg_data)
    
# ---------------------------------------------------------------------------
# Per-device worker
# ---------------------------------------------------------------------------
class OmniscanWorker:
    """Owns one Omniscan450. Receive loop publishes + forwards to shared log."""

    def __init__(
        self,
        node: Node,
        side: str,
        ip: str,
        tcp_port: int,
        publisher,
        frame_id: str,
        log_writer: SvlogWriter,
    ) -> None:
        self._node = node
        self._side = side
        self._ip = ip
        self._tcp_port = tcp_port
        self._publisher = publisher
        self._frame_id = frame_id
        self._log_writer = log_writer

        self._device: Optional[Omniscan450] = None
        self._thread: Optional[threading.Thread] = None
        self._running = threading.Event()
        self._control_lock = threading.Lock()
        self._pinging = False

    # ----- lifecycle -------------------------------------------------------
    def start(self) -> bool:
        log = self._node.get_logger()

        # logging=False -- we don't use brping's per-device logger, the
        # shared SvlogWriter handles file output for both sides.
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

        # Known clean state on the device side too.
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
            self._publish(data)
            # Forward the raw framed bytes to the shared svlog (no-op if
            # logging isn't active). brping populates msg_data inside
            # wait_message before returning.
            if data.msg_data:
                self._log_writer.write(bytes(data.msg_data))

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

        self.declare_parameter("log_directory", "data/SSS_data")

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

        # ---- Shared log writer (single file, both channels) ----------------
        log_root = Path(os.path.expanduser(self._str_param("log_directory")))
        port_ip = self._str_param("port_ip")
        port_tcp = self._int_param("port_tcp_port")
        starboard_ip = self._str_param("starboard_ip")
        starboard_tcp = self._int_param("starboard_tcp_port")

        self.get_logger().info(f"log directory: {log_root}")
        self._log_writer = SvlogWriter(
            log_dir=log_root,
            port_url=f"tcp://{port_ip}:{port_tcp}",
            starboard_url=f"tcp://{starboard_ip}:{starboard_tcp}",
        )

        # ---- Workers --------------------------------------------------------
        self._port_worker = OmniscanWorker(
            self,
            side="port",
            ip=port_ip,
            tcp_port=port_tcp,
            publisher=self._port_pub,
            frame_id=self._str_param("port_frame_id"),
            log_writer=self._log_writer,
        )
        self._starboard_worker = OmniscanWorker(
            self,
            side="starboard",
            ip=starboard_ip,
            tcp_port=starboard_tcp,
            publisher=self._starboard_pub,
            frame_id=self._str_param("starboard_frame_id"),
            log_writer=self._log_writer,
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
            "side_scan_sonar ready, ping OFF, log OFF. Toggle with:\n"
            "  ros2 topic pub --once /side_scan_sonar/ping/enable std_msgs/msg/Bool 'data: true'\n"
            "  ros2 topic pub --once /side_scan_sonar/log/enable  std_msgs/msg/Bool 'data: true'"
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
        if msg.data:
            path = self._log_writer.start()
            if path is not None:
                self.get_logger().info(f"logging -> {path}")
        else:
            path = self._log_writer.current_path
            self._log_writer.stop()
            if path is not None:
                self.get_logger().info(f"stopped logging ({path})")

    # ----- shutdown ---------------------------------------------------------
    def shutdown(self) -> None:
        self.get_logger().info("stopping side scan sonar node")
        self._log_writer.stop()
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
