"""Typed application configuration.

Defaults live here (single source of truth for types); the YAML file
``config/default.yaml`` overrides them and is the file operators edit in
the field. Unknown YAML keys raise immediately — a misspelled key in a
pre-experiment rush must fail loudly, not silently do nothing.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

import yaml


@dataclass
class RosTopics:
    """Every topic the application touches, in one place."""

    processed_ping: str = "/sss_processor/processed"
    odom: str = "/blueboat/odom"
    navsat: str = "/mavros/global_position/global"
    compass_hdg: str = "/mavros/global_position/compass_hdg"
    vfr_hud: str = "/mavros/vfr_hud"
    ping_enable: str = "/side_scan_sonar/ping/enable"
    svlog_enable: str = "/sss_processor/log/enable"
    # ---- placeholders (repositories not present yet) ----------------------
    detections: str = "/sss_ai/detections"     # see ros/detections_listener.py
    pinger: str = "/usbl/pinger/position"      # see ros/pinger_listener.py


@dataclass
class PipelineConfig:
    """START/STOP acquisition behaviour (bottom toolbar)."""

    # Command run by START. The app never launches sss_node.py: this launch
    # file starts the *processing* pipeline only (see launch/ directory).
    launch_command: List[str] = field(default_factory=lambda: [
        "ros2", "launch", "blueboat_sss", "SSS_processing_launch.py",
    ])
    # If true, START also publishes `true` on topics.ping_enable so the
    # already-running sss_node begins firing, and STOP publishes `false`.
    publish_ping_enable: bool = True
    # If true, START enables .svlog logging in the processor node.
    enable_svlog_on_start: bool = True
    # Delay between launching the pipeline and enabling pinging, to let
    # the processor node come up and subscribe.
    start_delay_s: float = 2.0
    stop_grace_s: float = 5.0


@dataclass
class MosaicConfig:
    cell_size_m: float = 0.25          # same rationale as the old listener
    initial_half_extent_m: float = 30.0
    render_hz: float = 4.0             # GUI raster refresh rate
    contrast_percentiles: List[float] = field(default_factory=lambda: [2.0, 98.0])


@dataclass
class InterpolationConfig:
    """Small-gap fill between consecutive sonar lines (render-time only)."""

    max_gap_m: float = 0.75     # never fill farther than this from real data
    min_neighbors: int = 3      # cells with fewer valid neighbours stay empty


@dataclass
class MapConfig:
    # Rotation between the local odom frame and ENU. mavros publishes local
    # position in ENU, so 0.0 is the correct default; override if the odom
    # frame is heading-aligned at boot.
    frame_yaw_offset_deg: float = 0.0
    # Background tile sources ({z}/{x}/{y} slippy scheme).
    osm_url: str = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    satellite_url: str = ("https://server.arcgisonline.com/ArcGIS/rest/services/"
                          "World_Imagery/MapServer/tile/{z}/{y}/{x}")
    use_satellite: bool = True
    tile_cache_dir: str = "~/.cache/blueboat_gcs/tiles"
    max_concurrent_tile_requests: int = 6


@dataclass
class SimConfig:
    """Built-in simulator (`--sim`) for bench-testing without ROS."""

    origin_lat: float = 43.6961
    origin_lon: float = 7.3080
    ping_hz: float = 15.0
    speed_mps: float = 0.8


@dataclass
class AppConfig:
    topics: RosTopics = field(default_factory=RosTopics)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    mosaic: MosaicConfig = field(default_factory=MosaicConfig)
    interpolation: InterpolationConfig = field(default_factory=InterpolationConfig)
    map: MapConfig = field(default_factory=MapConfig)
    sim: SimConfig = field(default_factory=SimConfig)
    data_root: str = "data/SSS_data"   # same root as the existing pipeline


def _apply(obj: Any, data: dict, path: str = "") -> None:
    for key, value in data.items():
        if not hasattr(obj, key):
            raise KeyError(f"Unknown config key: {path}{key}")
        current = getattr(obj, key)
        if dataclasses.is_dataclass(current) and isinstance(value, dict):
            _apply(current, value, path=f"{path}{key}.")
        else:
            setattr(obj, key, value)


def load_config(yaml_path: Optional[Path] = None) -> AppConfig:
    """Build the config from defaults, then overlay the YAML file if present."""
    cfg = AppConfig()
    if yaml_path is None:
        yaml_path = Path(__file__).parent / "default.yaml"
    if yaml_path.is_file():
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _apply(cfg, data)
    return cfg
