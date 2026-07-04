"""Main window — composition root of the GUI.

All wiring between data sources (signal bus), services (mosaic,
converter, launcher) and widgets (map, panels, toolbar) lives here and
only here; the individual modules know nothing about each other. To plug
a new ROS topic later: add a listener + model + signal, then connect it
in ``_connect_signals`` — nothing else changes.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QImage
from PySide6.QtWidgets import QDockWidget, QMainWindow, QScrollArea

from ..config.settings import AppConfig
from ..core.mosaic_service import MosaicService
from ..core.signals import AppSignals
from ..mapping.coordinate_converter import CoordinateConverter
from ..mapping.tiles import TileFetcher
from ..models.detection import Detection, PingerFix
from ..models.robot_state import RobotState
from . import left_panel as lp
from .left_panel import LeftPanel
from .map_layers import (DetectionLayer, MeasureLayer, MosaicLayer,
                         PingerLayer, TileLayer, TrajectoryLayer)
from .map_view import MapMode, MapView
from .right_panel import RightPanel
from .toolbar import AcquisitionToolbar


class MainWindow(QMainWindow):
    """BlueBoat GCS main window."""

    def __init__(self, config: AppConfig, signals: AppSignals,
                 mosaic_service: MosaicService,
                 acquisition_controller,  # PipelineLauncher or Simulator
                 ) -> None:
        super().__init__()
        self._config = config
        self._signals = signals
        self._mosaic_service = mosaic_service
        self._acquisition = acquisition_controller
        self._mission_start: Optional[float] = None
        self._last_robot_state: Optional[RobotState] = None

        self.setWindowTitle("BlueBoat GCS — Side-Scan Sonar Survey")
        self.resize(1500, 950)

        # ---- central map + layers -------------------------------------------
        self.map_view = MapView()
        self.setCentralWidget(self.map_view)
        scene = self.map_view.scene()

        self.converter = CoordinateConverter(config.map.frame_yaw_offset_deg)
        tile_url = (config.map.satellite_url if config.map.use_satellite
                    else config.map.osm_url)
        self._tile_fetcher = TileFetcher(
            tile_url, Path(config.map.tile_cache_dir).expanduser(),
            config.map.max_concurrent_tile_requests, parent=self)
        self.tile_layer = TileLayer(scene, self._tile_fetcher, self.converter)
        self.mosaic_layer = MosaicLayer(scene)
        self.trajectory_layer = TrajectoryLayer(scene)
        self.detection_layer = DetectionLayer(scene)
        self.pinger_layer = PingerLayer(scene)
        self.measure_layer = MeasureLayer(scene)

        # ---- side panels ------------------------------------------------------
        self.left_panel = LeftPanel()
        self.addDockWidget(Qt.LeftDockWidgetArea,
                           self._dock("Mission", self.left_panel))
        self.right_panel = RightPanel()
        self.addDockWidget(Qt.RightDockWidgetArea,
                           self._dock("Tools", self.right_panel))

        # ---- bottom toolbar + status bar ----------------------------------------
        self.toolbar = AcquisitionToolbar(self)
        self.addToolBar(Qt.BottomToolBarArea, self.toolbar)
        self.statusBar().showMessage("Ready.")

        self._mission_timer = QTimer(self)
        self._mission_timer.setInterval(1000)
        self._mission_timer.timeout.connect(self._update_mission_time)
        self._mission_timer.start()

        self._connect_signals()

    @staticmethod
    def _dock(title: str, widget) -> QDockWidget:
        dock = QDockWidget(title)
        dock.setFeatures(QDockWidget.DockWidgetMovable)
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(250)
        dock.setWidget(scroll)
        return dock

    # ---- wiring ----------------------------------------------------------------
    def _connect_signals(self) -> None:
        s = self._signals

        # Data streams (queued from the ROS thread) -> services & layers.
        s.sonar_ping.connect(self._mosaic_service.on_sonar_ping)
        s.robot_state.connect(self._on_robot_state)
        s.detection.connect(self._on_detection)
        s.pinger_fix.connect(self._on_pinger)
        s.pipeline_state.connect(self.toolbar.on_pipeline_state)
        s.status_message.connect(
            lambda msg: self.statusBar().showMessage(msg, 8000))
        self._mosaic_service.raster_updated.connect(self._on_raster)

        # Map interactions.
        self.map_view.point_clicked.connect(self._on_point_clicked)
        self.map_view.measure_started.connect(self._on_measure_started)
        self.map_view.measure_done.connect(self._on_measure_done)
        self.map_view.viewport_changed.connect(self._on_viewport_changed)

        # Left panel toggles.
        self.left_panel.layer_toggled.connect(self._on_layer_toggled)

        # Right panel tools.
        self.right_panel.zoom_in_clicked.connect(self.map_view.zoom_in)
        self.right_panel.zoom_out_clicked.connect(self.map_view.zoom_out)
        self.right_panel.center_robot_clicked.connect(self._center_robot)
        self.right_panel.measure_toggled.connect(self._on_measure_toggled)

        # Bottom toolbar.
        self.toolbar.start_clicked.connect(self._on_start)
        self.toolbar.stop_clicked.connect(self._on_stop)

    # ---- data slots (GUI thread) ---------------------------------------------------
    def _on_raster(self, image: QImage, extent: tuple, cell: float) -> None:
        self.mosaic_layer.update(image, extent, cell)

    def _on_robot_state(self, state: RobotState) -> None:
        self._last_robot_state = state
        self.left_panel.on_robot_state(state)
        self.trajectory_layer.add_pose(state.x, state.y, state.yaw)
        # Bind the GPS origin exactly once, on the first full state.
        if not self.converter.ready and state.lat is not None:
            self.converter.bind_origin(state.lat, state.lon, state.x, state.y)
            self._signals.origin_bound.emit(state.lat, state.lon)
            self.statusBar().showMessage(
                f"GPS origin bound at {state.lat:.6f}, {state.lon:.6f}", 8000)
            self._refresh_tiles()

    def _on_detection(self, det: Detection) -> None:
        self.left_panel.on_detection(det)
        self.detection_layer.upsert(det)

    def _on_pinger(self, fix: PingerFix) -> None:
        self.pinger_layer.update(fix)

    # ---- map interaction slots -------------------------------------------------------
    def _on_point_clicked(self, x: float, y: float) -> None:
        gps = self.converter.local_to_gps(x, y)
        self.left_panel.coordinate_card.set_point(x, y, gps)
        gps_txt = f"   |   {gps[0]:.7f}, {gps[1]:.7f}" if gps else ""
        self.statusBar().showMessage(
            f"Point:  x {x:+.2f} m,  y {y:+.2f} m{gps_txt}", 15000)

    def _on_measure_toggled(self, on: bool) -> None:
        self.map_view.set_mode(MapMode.MEASURE if on else MapMode.NAVIGATE)
        if not on:
            self.measure_layer.clear()

    def _on_measure_started(self, x: float, y: float) -> None:
        self.measure_layer.show_first(x, y)
        self.right_panel.on_first_point()
        self.right_panel.point_a.set_point(x, y, self.converter.local_to_gps(x, y))
        self.right_panel.point_b.clear()

    def _on_measure_done(self, x1: float, y1: float,
                         x2: float, y2: float, dist: float) -> None:
        self.measure_layer.show_measurement((x1, y1), (x2, y2), dist)
        self.right_panel.point_b.set_point(
            x2, y2, self.converter.local_to_gps(x2, y2))
        self.right_panel.show_distance(dist)

    def _on_viewport_changed(self, world_rect: QRectF, mpp: float) -> None:
        self.tile_layer.update_viewport(world_rect, mpp)

    def _refresh_tiles(self) -> None:
        self.tile_layer.update_viewport(self.map_view.world_viewport_rect(),
                                        self.map_view.metres_per_pixel())

    def _center_robot(self) -> None:
        pos = self.trajectory_layer.current_pos()
        if pos is None and self._last_robot_state is not None:
            pos = (self._last_robot_state.x, self._last_robot_state.y)
        if pos is not None:
            self.map_view.center_on_world(*pos)  # one-shot, camera stays free

    # ---- layer toggles ------------------------------------------------------------------
    def _on_layer_toggled(self, key: str, on: bool) -> None:
        if key == lp.LAYER_SATELLITE:
            self.tile_layer.set_visible(on)
            self.mosaic_layer.set_opacity(0.85 if on else 1.0)
            if on:
                self._refresh_tiles()
        elif key == lp.LAYER_TRAJECTORY:
            self.trajectory_layer.set_visible(on)
        elif key == lp.LAYER_PINGER:
            self.pinger_layer.set_visible(on)
        elif key == lp.LAYER_DETECTIONS:
            self.detection_layer.set_visible(on)
        elif key == lp.LAYER_INTERPOLATION:
            self._mosaic_service.set_interpolation(on)

    # ---- acquisition ---------------------------------------------------------------------
    def _on_start(self) -> None:
        self._mission_start = time.monotonic()
        self.trajectory_layer.clear()  # "trajectory since START"
        self._acquisition.start()

    def _on_stop(self) -> None:
        self._acquisition.stop()
        self._mission_start = None
        saved = self._mosaic_service.save()
        if saved is not None:
            self.statusBar().showMessage(f"Mosaic + trajectory saved to {saved}",
                                         15000)

    def _update_mission_time(self) -> None:
        self.left_panel.set_mission_time(
            None if self._mission_start is None
            else time.monotonic() - self._mission_start)

    # ---- shutdown --------------------------------------------------------------------------
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        self._acquisition.stop()
        self._mosaic_service.save()
        super().closeEvent(event)
