"""Main window — composition root of the GUI.

Wires together the data store, the signal bus, the panels, the map and the
toolbar.  Owns the single 10 Hz refresh timer that drives all repainting
(messages update the store immediately; widgets repaint on the tick — this
is what keeps the UI smooth and flicker-free during long experiments).
"""

from __future__ import annotations

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QSplitter, QStatusBar,
    QVBoxLayout, QWidget,
)

from mcs.config.settings import AppConfig
from mcs.core.signals import SignalBus
from mcs.gui import theme
from mcs.gui.bottom_toolbar import BottomToolbar
from mcs.gui.left_panel import LeftPanel
from mcs.gui.map.map_view import MapMode, MapView
from mcs.gui.right_panel import RightPanel
from mcs.models.store import DataStore
from mcs.ros.command_center import CommandCenter
from mcs.ros.launch_manager import LaunchManager, LaunchParameters
from mcs.ros.ros_manager import RosManager

_LOG = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """The BlueBoat Mission Control Station main window."""

    def __init__(self, cfg: AppConfig) -> None:
        super().__init__()
        self.setWindowTitle("BlueBoat Mission Control Station")
        self.resize(1500, 900)
        self._exit_in_progress = False
        self._exit_finalized = False
        self._exit_deadline = 0.0

        # ---- Core objects ----------------------------------------------------
        self.cfg = cfg
        self.bus = SignalBus()
        self.store = DataStore(cfg)
        self.ros = RosManager(cfg, self.bus)
        self.launcher = LaunchManager(cfg, self.bus)
        self.commands = CommandCenter(cfg, self.bus, self.ros, self.launcher)

        # ---- Widgets -----------------------------------------------------------
        self.map_view = MapView(cfg, self.store)
        self.left_panel = LeftPanel(cfg, self.store)
        self.right_panel = RightPanel(cfg, self.store)
        self.toolbar = BottomToolbar(cfg, self.bus, self.launcher, self.commands)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.map_view)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 0)
        layout.setSpacing(4)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self.toolbar)
        self.setCentralWidget(central)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._inspect_label = QLabel("")
        self._inspect_label.setObjectName("valueLabel")
        self._status.addWidget(self._inspect_label, stretch=1)
        self._geo_label = QLabel("georef: —")
        self._status.addPermanentWidget(self._geo_label)
        self._ros_label = QLabel("ROS: starting…")
        self._status.addPermanentWidget(self._ros_label)

        self._connect_signals()

        # ---- Refresh tick -----------------------------------------------------
        period_ms = int(1000.0 / cfg.map.ui_refresh_hz)
        self._tick = QTimer(self)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start(period_ms)

        # ---- Go ------------------------------------------------------------------
        self.ros.start()
        self._ros_label.setText(
            "ROS: connected" if self.ros.running else "ROS: unavailable")

    # ============================================================== signal wiring
    def _connect_signals(self) -> None:
        bus, store = self.bus, self.store

        # Telemetry → store (queued into the GUI thread by Qt)
        bus.odom_received.connect(store.on_odom)
        bus.gps_received.connect(store.on_gps)
        bus.mavros_state_received.connect(store.on_mavros_state)
        bus.pinger_body_received.connect(store.on_pinger_body)
        bus.uw_gps_raw_received.connect(store.on_uw_gps_raw)
        bus.monitoring_received.connect(store.on_monitoring)
        bus.thruster_received.connect(store.on_thruster)
        bus.controller_ready_received.connect(store.on_controller_ready)
        bus.param_mode_received.connect(store.on_param_mode)
        bus.mission_path_received.connect(store.on_mission_path)
        bus.mission_path_failed.connect(
            lambda err: self._status.showMessage(f"Path request failed: {err}", 5000))

        # Diagnostics / logs.
        # Each message is fanned out from ONE signal to BOTH sinks — the GUI
        # (operator-friendly) and the python logger (terminal = complete debug
        # output) — so the two can never desynchronize.
        bus.topic_stats_updated.connect(self.left_panel.on_topic_stats)
        bus.ros_log.connect(lambda msg: self._status.showMessage(msg, 8000))
        bus.ros_log.connect(lambda msg: _LOG.info("ros: %s", msg))
        bus.command_sent.connect(
            lambda desc: self._status.showMessage(f"Published: {desc}", 4000))
        bus.command_sent.connect(lambda desc: _LOG.info("published: %s", desc))
        bus.launch_state_changed.connect(
            lambda s: _LOG.info("launch state: %s", s))
        bus.estop_state_changed.connect(
            lambda s: _LOG.warning("safe-shutdown phase: %s", s)
            if s != "idle" else None)
        # Launch process output: dedicated GUI console (right panel) + DEBUG
        # level on the terminal (visible with --verbose), order-preserving in
        # both since one queued signal drives both slots.
        bus.launch_output.connect(self.right_panel.console.append_line)
        bus.launch_output.connect(lambda line: _LOG.debug("[launch] %s", line))

        # Panels ↔ map
        self.left_panel.layer_toggled.connect(self.map_view.set_layer_visible)
        self.right_panel.time_window_changed.connect(self.map_view.set_time_window)
        self.right_panel.zoom_in_requested.connect(self.map_view.zoom_in)
        self.right_panel.zoom_out_requested.connect(self.map_view.zoom_out)
        self.right_panel.center_robot_requested.connect(self.map_view.center_on_robot)
        self.map_view.point_inspected.connect(self._inspect_label.setText)

        # Toolbar
        self.toolbar.manual_target_mode_changed.connect(self._on_manual_mode)
        self.toolbar.measure_mode_changed.connect(self._on_measure_mode)
        self.toolbar.mission_launched.connect(self._on_mission_launched)
        self.toolbar.mission_stopped.connect(self._on_mission_stopped)
        bus.launch_state_changed.connect(self._on_launch_state)

        # Manual target clicks
        self.map_view.target_clicked.connect(self._on_target_clicked)

    # ================================================================ tick
    def _on_tick(self) -> None:
        self.left_panel.refresh()
        self.right_panel.refresh()
        self.map_view.refresh()
        # Georeference status + satellite availability
        geo = self.store.geo
        if geo.fit is None:
            self._geo_label.setText("georef: collecting…")
        else:
            quality = "ok" if geo.is_valid else "poor"
            color = theme.OK if geo.is_valid else theme.WARN
            self._geo_label.setText(
                f"georef: {quality} (rms {geo.fit.rms_m:.1f} m)")
            self._geo_label.setStyleSheet(f"color: {color};")
        self.left_panel.set_satellite_available(geo.is_valid)
        # Mission readiness → launch state promotion. The FCU-connected check
        # only applies to the real-robot graph; Sim_launch.py has no MAVROS.
        if self.launcher.state == "starting":
            fcu_ok = (self.store.robot.fcu_connected
                      or self.store.mission.simulation)
            if fcu_ok and self.store.robot.has_odom:
                self.launcher.notify_running()

    # ============================================================ mission events
    def _on_mission_launched(self, params: LaunchParameters) -> None:
        m = self.store.mission
        m.launch_running = True
        m.controller_type = params.controller_type
        m.use_pinger = params.use_pinger
        m.simulation = params.simulation
        m.manual_target = None
        self.commands.set_simulation_mode(params.simulation)
        self.store.reset_experiment()
        # Fetch the mission path for display once the service is up.
        # Sim_launch.py always starts path_generation; the real launch only
        # does so with a controller and use_pinger:=False.
        if params.simulation or (params.controller_type and not params.use_pinger):
            QTimer.singleShot(3000, lambda: self.commands.request_mission_path())

    def _on_mission_stopped(self) -> None:
        pass  # state cleared on 'idle' launch_state

    def _on_launch_state(self, state: str) -> None:
        if state == "idle":
            self.store.mission.launch_running = False
            self.store.mission.manual_target = None
            self.store.mission.simulation = False
            self.commands.set_simulation_mode(False)
            if self.toolbar.manual_button.isChecked():
                self.toolbar.manual_button.setChecked(False)

    # ============================================================ manual target
    def _on_manual_mode(self, on: bool) -> None:
        if on:
            self.map_view.set_mode(MapMode.MANUAL_TARGET)
            self._status.showMessage(
                "Manual Target mode: click the map to send a target. "
                "Click the button again to resume the original mission.", 8000)
        else:
            self.map_view.set_mode(MapMode.NORMAL)
            # Deactivation publishes [0.0, 0.0] → master_control resumes mission.
            self.commands.resume_original_mission()
            self.store.mission.manual_target = None
            self.map_view.clear_manual_target()

    def _on_target_clicked(self, x: float, y: float) -> None:
        if x == 0.0 and y == 0.0:
            # (0,0) is the reserved resume sentinel of master_control — nudge it.
            x = 1e-3
        self.commands.publish_manual_target(x, y)
        self.store.mission.manual_target = (x, y)
        self.map_view.show_manual_target(x, y)

    def _on_measure_mode(self, on: bool) -> None:
        if on and self.toolbar.manual_button.isChecked():
            self.toolbar.manual_button.setChecked(False)
        self.map_view.set_mode(MapMode.MEASURE if on else MapMode.NORMAL)

    # ================================================================ shutdown
    def closeEvent(self, event: QCloseEvent) -> None:
        """Application Exit is a node-termination path, so it must honour the
        same guarantee as E-STOP / Stop Mission: 'default' is published and
        its transmission confirmed BEFORE any node dies. The sequence is
        asynchronous, so the first close is deferred (event.ignore()) while
        CommandCenter.safe_app_exit runs; the window closes itself again once
        the sequence — and the launch-process exit — have completed."""
        if self._exit_finalized:
            self.ros.stop()
            event.accept()
            return
        if self.launcher.running:
            if not self._exit_in_progress:
                answer = QMessageBox.question(
                    self, "Mission running",
                    "A mission is still running. Publish 'default', stop the "
                    "nodes safely and quit?",
                    QMessageBox.StandardButton.Yes
                    | QMessageBox.StandardButton.Cancel)
                if answer != QMessageBox.StandardButton.Yes:
                    event.ignore()
                    return
                self._exit_in_progress = True
                self.bus.shutdown_sequence_finished.connect(self._on_exit_sequence_done)
                self.commands.safe_app_exit()
            event.ignore()  # keep the process (and the DDS writer) alive
            return
        self.ros.stop()
        event.accept()

    def _on_exit_sequence_done(self) -> None:
        """Safe-shutdown confirmed; now wait for the launch tree to exit."""
        self.bus.shutdown_sequence_finished.disconnect(self._on_exit_sequence_done)
        self._exit_deadline = 0.0
        self._poll_exit_ready()

    def _poll_exit_ready(self) -> None:
        # Give the SIGINT→SIGTERM→SIGKILL escalation (driven by QTimers that
        # need the event loop) up to its own budget before finalizing anyway.
        budget_s = (self.cfg.launch.sigint_timeout_s
                    + self.cfg.launch.sigterm_timeout_s + 3.0)
        self._exit_deadline += 0.2
        if self.launcher.running and self._exit_deadline < budget_s:
            QTimer.singleShot(200, self._poll_exit_ready)
            return
        self._exit_finalized = True
        self.close()  # re-enters closeEvent on the finalized branch
