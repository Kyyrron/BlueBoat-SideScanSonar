#!/usr/bin/env python3
"""
Convert a SonarView .svlog file into a ROS 2 rosbag2 directory replayable
into sss_processor_node, bypassing sss_node entirely.

The output bag carries every topic sss_processor consumes:

    /side_scan_sonar/port/profile        blueboat_interfaces/OmniscanProfile
    /side_scan_sonar/port/raw            std_msgs/UInt8MultiArray
    /side_scan_sonar/starboard/profile   blueboat_interfaces/OmniscanProfile
    /side_scan_sonar/starboard/raw       std_msgs/UInt8MultiArray
    /mavros/imu/data                     sensor_msgs/Imu
    /mavros/global_position/global       sensor_msgs/NavSatFix
    /mavros/global_position/rel_alt      std_msgs/Float64
    /mavros/global_position/compass_hdg  std_msgs/Float64
    /blueboat/odom                       nav_msgs/Odometry  (synthesized from
                                         mavlink LOCAL_POSITION_NED + ATTITUDE)

The reverse direction (rosbag2 -> .svlog) is what sss_processor_node already
does at runtime: replay a bag captured by this script with logging enabled
and you get a fresh .svlog out the other side.

Notes:
* The svlog packet headers have no timestamp; we assign a synthetic clock
  that advances by `NS_PER_PACKET` per packet in file order. The interval
  is well under the processor's 50 ms port/stbd pairing tolerance.
* /blueboat/odom is synthesized when both an ATTITUDE and a
  LOCAL_POSITION_NED have been seen. Mavlink LOCAL_POSITION_NED is in NED
  frame; the resulting odom uses ENU (REP-103), matching typical ROS odom.
* sss_node publishes the on-wire packet bytes with byte 6 (src) = 0 (the
  Omniscan emits packets with src=0). The svlog file has byte 6 retagged
  to 1 or 2 by the processor's writer. We retag back to 0 when writing
  the raw topic so the rosbag faithfully replays what sss_node produces.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Iterator, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rclpy
from rclpy.serialization import serialize_message

from rosbag2_py import (
    SequentialWriter,
    StorageOptions,
    ConverterOptions,
    TopicMetadata,
)

from builtin_interfaces.msg import Time as TimeMsg
from std_msgs.msg import Float64, UInt8MultiArray
from sensor_msgs.msg import Imu, NavSatFix
from nav_msgs.msg import Odometry

from blueboat_interfaces.msg import OmniscanProfile

from svlog import (
    DEVICE_ID_PORT,
    DEVICE_ID_STBD,
    MAVLINK_WRAPPER_ID,
    OS_MONO_PROFILE_ID,
    retag_packet_src_device_id,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TOPIC_PORT_PROFILE = "/side_scan_sonar/port/profile"
TOPIC_STBD_PROFILE = "/side_scan_sonar/starboard/profile"
TOPIC_PORT_RAW     = "/side_scan_sonar/port/raw"
TOPIC_STBD_RAW     = "/side_scan_sonar/starboard/raw"
TOPIC_IMU          = "/mavros/imu/data"
TOPIC_NAVSAT       = "/mavros/global_position/global"
TOPIC_REL_ALT      = "/mavros/global_position/rel_alt"
TOPIC_COMPASS_HDG  = "/mavros/global_position/compass_hdg"
TOPIC_ODOM         = "/blueboat/odom"

# Synthetic clock: 5 ms between consecutive packets. With ~9-10k packets
# per minute of real recording this gives a ~50 s replay for a typical file
# -- compressed but monotonic and within all timing tolerances downstream.
NS_PER_PACKET: int = 5_000_000

# Fixed epoch for synthesized stamps (Jan 1 2024 00:00:00 UTC).
EPOCH_NS: int = 1_704_067_200 * 1_000_000_000

# OS_MONO_PROFILE payload format (per brping Omniscan450 template):
# u32 ping_number, u32 start_mm, u32 length_mm, u32 timestamp_ms, u32 ping_hz,
# u16 gain_index, u16 num_results, u16 sos_dmps,
# u8 channel_number, u8 reserved,
# f32 pulse_duration_sec, f32 analog_gain, f32 max_pwr_db, f32 min_pwr_db,
# f32 transducer_heading_deg, f32 vehicle_heading_deg,
# then num_results × u16 power samples.
_OS_MONO_PROFILE_HEAD_FMT: str = "<IIIIIHHHBBffffff"
_OS_MONO_PROFILE_HEAD_SIZE: int = struct.calcsize(_OS_MONO_PROFILE_HEAD_FMT)


# ---------------------------------------------------------------------------
# Pure-data helpers (no ROS deps; unit-testable in isolation)
# ---------------------------------------------------------------------------
def walk_packets(data: bytes) -> Iterator[bytes]:
    """Yield framed packet bytes from a svlog stream, skipping junk."""
    pos = 0
    n = len(data)
    while pos < n - 8:
        if data[pos:pos + 2] != b"BR":
            pos += 1
            continue
        plen = struct.unpack_from("<H", data, pos + 2)[0]
        total = 8 + plen + 2
        if pos + total > n:
            return  # truncated tail
        yield data[pos:pos + total]
        pos += total


def decode_os_mono_profile(payload: bytes) -> dict:
    """Decode an OS_MONO_PROFILE payload (packet_id=2198) to named fields."""
    if len(payload) < _OS_MONO_PROFILE_HEAD_SIZE:
        raise ValueError(
            f"OS_MONO_PROFILE payload too short: {len(payload)} bytes"
        )
    (ping_number, start_mm, length_mm, timestamp_ms, ping_hz,
     gain_index, num_results, sos_dmps, channel_number, _reserved,
     pulse_duration_sec, analog_gain, max_pwr_db, min_pwr_db,
     transducer_heading_deg, vehicle_heading_deg) = struct.unpack(
        _OS_MONO_PROFILE_HEAD_FMT,
        payload[:_OS_MONO_PROFILE_HEAD_SIZE],
    )
    expected = _OS_MONO_PROFILE_HEAD_SIZE + 2 * num_results
    if len(payload) < expected:
        raise ValueError(
            f"OS_MONO_PROFILE payload truncated: "
            f"expect {expected} bytes for {num_results} samples, got {len(payload)}"
        )
    pwr_results = list(struct.unpack(
        f"<{num_results}H",
        payload[_OS_MONO_PROFILE_HEAD_SIZE:_OS_MONO_PROFILE_HEAD_SIZE + 2 * num_results],
    ))
    return {
        "ping_number": ping_number,
        "start_mm": start_mm,
        "length_mm": length_mm,
        "timestamp_ms": timestamp_ms,
        "ping_hz": ping_hz,
        "gain_index": gain_index,
        "num_results": num_results,
        "sos_dmps": sos_dmps,
        "channel_number": channel_number,
        "pulse_duration_sec": pulse_duration_sec,
        "analog_gain": analog_gain,
        "max_pwr_db": max_pwr_db,
        "min_pwr_db": min_pwr_db,
        "transducer_heading_deg": transducer_heading_deg,
        "vehicle_heading_deg": vehicle_heading_deg,
        "pwr_results": pwr_results,
    }


def rpy_to_quat(roll: float, pitch: float, yaw: float) -> Tuple[float, float, float, float]:
    """ZYX intrinsic Euler -> (x, y, z, w) quaternion (ROS convention)."""
    cy, sy = math.cos(yaw * 0.5),   math.sin(yaw * 0.5)
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cr, sr = math.cos(roll * 0.5),  math.sin(roll * 0.5)
    return (
        sr * cp * cy - cr * sp * sy,  # x
        cr * sp * cy + sr * cp * sy,  # y
        cr * cp * sy - sr * sp * cy,  # z
        cr * cp * cy + sr * sp * sy,  # w
    )


def ned_to_enu_xyz(x_n: float, y_e: float, z_d: float) -> Tuple[float, float, float]:
    """Mavlink LOCAL_POSITION_NED -> ROS REP-103 ENU."""
    return (y_e, x_n, -z_d)


def ns_to_time_msg(ns: int) -> TimeMsg:
    t = TimeMsg()
    t.sec = ns // 1_000_000_000
    t.nanosec = ns % 1_000_000_000
    return t


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------
class Converter:
    """Stateful svlog -> rosbag2 converter."""

    def __init__(self, writer: SequentialWriter) -> None:
        self._writer = writer
        self._next_ns = EPOCH_NS

        # Latest values used to synthesize /blueboat/odom.
        self._latest_quat: Optional[Tuple[float, float, float, float]] = None
        self._latest_lpn: Optional[dict] = None

        # Summary counters.
        self.counts = {
            "sonar_port":           0,
            "sonar_stbd":           0,
            "imu":                  0,
            "navsat":               0,
            "rel_alt":              0,
            "compass_hdg":          0,
            "odom_synthesized":     0,
            "mavlink_other_type":   0,
            "skipped_non_target":   0,
            "decode_errors":        0,
        }

    # ---- timestamp -----------------------------------------------------
    def _next_stamp_ns(self) -> int:
        ns = self._next_ns
        self._next_ns += NS_PER_PACKET
        return ns

    # ---- topic setup ---------------------------------------------------
    def setup_topics(self) -> None:
        topics = [
            (TOPIC_PORT_PROFILE, "blueboat_interfaces/msg/OmniscanProfile"),
            (TOPIC_STBD_PROFILE, "blueboat_interfaces/msg/OmniscanProfile"),
            (TOPIC_PORT_RAW,     "std_msgs/msg/UInt8MultiArray"),
            (TOPIC_STBD_RAW,     "std_msgs/msg/UInt8MultiArray"),
            (TOPIC_IMU,          "sensor_msgs/msg/Imu"),
            (TOPIC_NAVSAT,       "sensor_msgs/msg/NavSatFix"),
            (TOPIC_REL_ALT,      "std_msgs/msg/Float64"),
            (TOPIC_COMPASS_HDG,  "std_msgs/msg/Float64"),
            (TOPIC_ODOM,         "nav_msgs/msg/Odometry"),
        ]
        for name, type_name in topics:
            self._writer.create_topic(
                TopicMetadata(
                    id=0,
                    name=name,
                    type=type_name,
                    serialization_format="cdr",
                    offered_qos_profiles=[]
                )
            )

    # ---- packet entry point --------------------------------------------
    def handle_packet(self, packet: bytes) -> None:
        pid = struct.unpack_from("<H", packet, 4)[0]
        src = packet[6]
        payload = packet[8:-2]  # strip 8-byte header and 2-byte checksum

        if pid == OS_MONO_PROFILE_ID:
            self._handle_sonar(packet, src, payload)
        elif pid == MAVLINK_WRAPPER_ID:
            try:
                envelope = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self.counts["decode_errors"] += 1
                return
            self._handle_mavlink(envelope)
        else:
            # JSON_META, VIEW_CONFIG, Omniscan settings (2194), EOS (0), ...
            self.counts["skipped_non_target"] += 1

    # ---- sonar ---------------------------------------------------------
    def _handle_sonar(self, packet: bytes, src: int, payload: bytes) -> None:
        if src == DEVICE_ID_PORT:
            side, topic_prof, topic_raw = "port", TOPIC_PORT_PROFILE, TOPIC_PORT_RAW
        elif src == DEVICE_ID_STBD:
            side, topic_prof, topic_raw = "stbd", TOPIC_STBD_PROFILE, TOPIC_STBD_RAW
        else:
            # Untagged or unexpected device_id; can't route.
            self.counts["skipped_non_target"] += 1
            return

        try:
            d = decode_os_mono_profile(payload)
        except ValueError:
            self.counts["decode_errors"] += 1
            return

        stamp_ns = self._next_stamp_ns()
        stamp = ns_to_time_msg(stamp_ns)

        prof = OmniscanProfile()
        prof.header.stamp = stamp
        prof.header.frame_id = f"sss_{side}_link"
        prof.side = side
        prof.ping_number           = d["ping_number"]
        prof.start_mm              = d["start_mm"]
        prof.length_mm             = d["length_mm"]
        prof.timestamp_ms          = d["timestamp_ms"]
        prof.ping_hz               = d["ping_hz"]
        prof.gain_index            = d["gain_index"]
        prof.num_results           = d["num_results"]
        prof.sos_dmps              = d["sos_dmps"]
        prof.channel_number        = d["channel_number"]
        prof.pulse_duration_sec    = float(d["pulse_duration_sec"])
        prof.analog_gain           = float(d["analog_gain"])
        prof.max_pwr_db            = float(d["max_pwr_db"])
        prof.min_pwr_db            = float(d["min_pwr_db"])
        prof.transducer_heading_deg = float(d["transducer_heading_deg"])
        prof.vehicle_heading_deg   = float(d["vehicle_heading_deg"])
        prof.pwr_results           = d["pwr_results"]

        # Raw bytes: retag src back to 0 so the rosbag faithfully mirrors
        # what sss_node would have published (sss_node publishes the
        # device's on-wire bytes verbatim; the Omniscan emits src=0).
        raw = UInt8MultiArray()
        raw.data = list(retag_packet_src_device_id(packet, 0))

        self._writer.write(topic_prof, serialize_message(prof), stamp_ns)
        self._writer.write(topic_raw,  serialize_message(raw),  stamp_ns)
        self.counts[f"sonar_{side}"] += 1

    # ---- mavlink dispatch ----------------------------------------------
    def _handle_mavlink(self, envelope: dict) -> None:
        m = envelope.get("message", {})
        msg_type = m.get("type")
        if msg_type == "ATTITUDE":
            self._emit_attitude(m)
        elif msg_type == "GLOBAL_POSITION_INT":
            self._emit_global_position(m)
        elif msg_type == "LOCAL_POSITION_NED":
            self._emit_local_position(m)
        else:
            self.counts["mavlink_other_type"] += 1

    def _emit_attitude(self, m: dict) -> None:
        roll  = float(m.get("roll",  0.0))
        pitch = float(m.get("pitch", 0.0))
        yaw   = float(m.get("yaw",   0.0))
        qx, qy, qz, qw = rpy_to_quat(roll, pitch, yaw)
        self._latest_quat = (qx, qy, qz, qw)

        stamp_ns = self._next_stamp_ns()
        imu = Imu()
        imu.header.stamp = ns_to_time_msg(stamp_ns)
        imu.header.frame_id = "base_link"
        imu.orientation.x = qx
        imu.orientation.y = qy
        imu.orientation.z = qz
        imu.orientation.w = qw
        imu.angular_velocity.x = float(m.get("rollspeed",  0.0))
        imu.angular_velocity.y = float(m.get("pitchspeed", 0.0))
        imu.angular_velocity.z = float(m.get("yawspeed",   0.0))
        # Linear acceleration: not present in mavlink ATTITUDE -> zeros.

        self._writer.write(TOPIC_IMU, serialize_message(imu), stamp_ns)
        self.counts["imu"] += 1

        # ATTITUDE arrival may complete a fresh odom estimate.
        self._maybe_publish_odom(stamp_ns)

    def _emit_global_position(self, m: dict) -> None:
        stamp_ns = self._next_stamp_ns()
        stamp = ns_to_time_msg(stamp_ns)

        fix = NavSatFix()
        fix.header.stamp = stamp
        fix.header.frame_id = "base_link"
        fix.status.status  = 0   # STATUS_FIX
        fix.status.service = 1   # SERVICE_GPS
        fix.latitude  = float(m.get("lat", 0)) / 1e7
        fix.longitude = float(m.get("lon", 0)) / 1e7
        fix.altitude  = float(m.get("alt", 0)) / 1000.0   # mm AMSL -> m
        self._writer.write(TOPIC_NAVSAT, serialize_message(fix), stamp_ns)
        self.counts["navsat"] += 1

        rel = Float64()
        rel.data = float(m.get("relative_alt", 0)) / 1000.0   # mm -> m
        self._writer.write(TOPIC_REL_ALT, serialize_message(rel), stamp_ns)
        self.counts["rel_alt"] += 1

        hdg = Float64()
        hdg.data = float(m.get("hdg", 0)) / 100.0             # cdeg -> deg
        self._writer.write(TOPIC_COMPASS_HDG, serialize_message(hdg), stamp_ns)
        self.counts["compass_hdg"] += 1

    def _emit_local_position(self, m: dict) -> None:
        self._latest_lpn = {
            "x":  float(m.get("x",  0.0)),
            "y":  float(m.get("y",  0.0)),
            "z":  float(m.get("z",  0.0)),
            "vx": float(m.get("vx", 0.0)),
            "vy": float(m.get("vy", 0.0)),
            "vz": float(m.get("vz", 0.0)),
        }
        stamp_ns = self._next_stamp_ns()
        self._maybe_publish_odom(stamp_ns)

    # ---- odom synthesis ------------------------------------------------
    def _maybe_publish_odom(self, stamp_ns: int) -> None:
        if self._latest_quat is None or self._latest_lpn is None:
            return
        qx, qy, qz, qw = self._latest_quat
        lpn = self._latest_lpn

        odom = Odometry()
        odom.header.stamp = ns_to_time_msg(stamp_ns)
        odom.header.frame_id = "odom"
        odom.child_frame_id = "base_link"
        # NED -> ENU (REP-103). Twist similarly transformed.
        px, py, pz = ned_to_enu_xyz(lpn["x"], lpn["y"], lpn["z"])
        vx, vy, vz = ned_to_enu_xyz(lpn["vx"], lpn["vy"], lpn["vz"])
        odom.pose.pose.position.x = px
        odom.pose.pose.position.y = py
        odom.pose.pose.position.z = pz
        odom.pose.pose.orientation.x = qx
        odom.pose.pose.orientation.y = qy
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x = vx
        odom.twist.twist.linear.y = vy
        odom.twist.twist.linear.z = vz
        self._writer.write(TOPIC_ODOM, serialize_message(odom), stamp_ns)
        self.counts["odom_synthesized"] += 1


def main() -> None:

    INPUT_FILE = "55_svlog.svlog"
    OUTPUT_BAG = "./output_bag" # Must not exist
    STORAGE_FORMAT = "mcap"

    input_path = Path(INPUT_FILE)
    output_path = Path(OUTPUT_BAG)

    if not input_path.is_file():
        sys.exit("input file not found")

    if output_path.exists():
        sys.exit("output already exists")

    rclpy.init()

    try:
        writer = SequentialWriter()

        writer.open(
            StorageOptions(
                uri=str(output_path),
                storage_id=STORAGE_FORMAT,
            ),
            ConverterOptions(
                input_serialization_format="cdr",
                output_serialization_format="cdr",
            ),
        )

        conv = Converter(writer)
        conv.setup_topics()

        data = input_path.read_bytes()
        n = 0

        for packet in walk_packets(data):
            conv.handle_packet(packet)
            n += 1
        # Force the writer to close cleanly before rclpy shutdown.
        del writer

        print(f"Converted {n} packets from {input_path.name} -> {output_path.name}")
        for k, v in sorted(conv.counts.items()):
            print(f"  {k:>22s}: {v}")
    finally:
        rclpy.shutdown()


if __name__ == "__main__":
    main()