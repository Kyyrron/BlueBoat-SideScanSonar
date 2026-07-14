"""Bottom mission-control toolbar.

Buttons (left → right):

* **Launch Mission** — opens the configuration dialog, then starts
  ``ros2 launch`` through the :class:`~mcs.ros.launch_manager.LaunchManager`.
* **Stop Mission** — graceful SIGINT-first shutdown; the station stays open.
* **EMERGENCY STOP** — sequenced: publish ``default`` on
  ``/blueboat/input_str``, wait for confirmation, then (optionally)
  terminate nodes.  Never disabled while ROS is up.
* **Publish Default/Override Control Mode** — alternates the two commands.
* **Manual Target** / **Continue Original Mission** — toggles the map's
  manual-target mode; deactivation publishes ``[0.0, 0.0]``.
* **Measure** — toggles the distance tool.
* A one-line launch console + launch state LED.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from mcs.config.settings import AppConfig
from mcs.core.signals import SignalBus
from mcs.gui import theme
from mcs.gui.dialogs.launch_dialog import LaunchDialog
from mcs.gui.widgets import StatusLed
from mcs.ros.command_center import CommandCenter
from mcs.ros.launch_manager import LaunchManager


class BottomToolbar(QWidget):
    """Mission control strip along the bottom of the main window."""

    manual_target_mode_changed = Signal(bool)
    measure_mode_changed = Signal(bool)
    mission_launched = Signal(object)   # LaunchParameters
    mission_stopped = Signal()

    def __init__(self, cfg: AppConfig, bus: SignalBus, launcher: LaunchManager,
                 commands: CommandCenter, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cfg = cfg
        self._bus = bus
        self._launcher = launcher
        self._commands = commands

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 6)
        outer.setSpacing(3)

        row = QHBoxLayout()
        row.setSpacing(8)
        outer.addLayout(row)

        self._launch_led = StatusLed(12)
        row.addWidget(self._launch_led)

        self.launch_button = QPushButton("Launch Mission")
        self.launch_button.setObjectName("launchButton")
        self.launch_button.clicked.connect(self._on_launch)
        row.addWidget(self.launch_button)

        self.stop_button = QPushButton("Stop Mission")
        self.stop_button.setEnabled(False)
        self.stop_button.setToolTip(
            "Publishes 'default' on /blueboat/input_str, waits for confirmed "
            "transmission, then gracefully stops every launched node.")
        self.stop_button.clicked.connect(self._on_stop)
        row.addWidget(self.stop_button)

        row.addSpacing(14)

        self.estop_button = QPushButton("EMERGENCY STOP")
        self.estop_button.setObjectName("estopButton")
        self.estop_button.clicked.connect(self._on_estop)
        row.addWidget(self.estop_button)

        self.mode_button = QPushButton()
        self.mode_button.clicked.connect(self._on_mode_toggle)
        row.addWidget(self.mode_button)
        self._refresh_mode_button()

        row.addSpacing(14)

        self.manual_button = QPushButton("Manual Target")
        self.manual_button.setCheckable(True)
        self.manual_button.toggled.connect(self._on_manual_toggled)
        row.addWidget(self.manual_button)

        self.measure_button = QPushButton("Measure")
        self.measure_button.setCheckable(True)
        self.measure_button.toggled.connect(self.measure_mode_changed.emit)
        row.addWidget(self.measure_button)

        row.addStretch(1)

        self._estop_label = QLabel("")
        self._estop_label.setStyleSheet(f"color: {theme.WARN}; font-weight: bold;")
        row.addWidget(self._estop_label)

        self._console = QLabel("")
        self._console.setStyleSheet(
            f"color: {theme.TEXT_DIM}; font-family: 'DejaVu Sans Mono', monospace;"
            "font-size: 10px;")
        self._console.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(self._console)

        bus.launch_state_changed.connect(self._on_launch_state)
        bus.launch_output.connect(self._on_launch_output)
        bus.estop_state_changed.connect(self._on_estop_state)

    # ================================================================ actions
    def _on_launch(self) -> None:
        dialog = LaunchDialog(self._cfg, self._launcher.last_parameters, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return
        params = dialog.parameters()
        if params.enable_motors:
            confirm = QMessageBox.warning(
                self, "Motors enabled",
                "Motors are ENABLED for this launch — the boat will actually "
                "move.\n\nProceed?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if confirm != QMessageBox.StandardButton.Yes:
                return
        if self._launcher.start(params):
            self.mission_launched.emit(params)

    def _on_stop(self) -> None:
        # Stop Mission is also a node-termination path, so it runs the same
        # guarantee as E-STOP: publish 'default', confirm transmission, and
        # only then terminate (CommandCenter.safe_shutdown — never a direct
        # launcher.stop()).
        self._commands.safe_stop_mission()
        self.mission_stopped.emit()

    def _on_estop(self) -> None:
        box = QMessageBox(self)
        box.setWindowTitle("Emergency Stop")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Publish 'default' on /blueboat/input_str now.\n"
                    "Also terminate all launched nodes afterwards?")
        publish_only = box.addButton("E-STOP only", QMessageBox.ButtonRole.AcceptRole)
        publish_kill = box.addButton("E-STOP + terminate nodes",
                                     QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is publish_only:
            self._commands.emergency_stop(terminate_nodes=False)
        elif clicked is publish_kill:
            self._commands.emergency_stop(terminate_nodes=True)

    def _on_mode_toggle(self) -> None:
        self._commands.publish_mode_toggle()
        self._refresh_mode_button()

    def _refresh_mode_button(self) -> None:
        nxt = self._commands.next_mode_command
        self.mode_button.setText(f"Publish {nxt.capitalize()} Control Mode")
        self.mode_button.setToolTip(
            f"Publishes String('{nxt}') on {self._cfg.topics.input_str}; "
            "the button then alternates to the other command.")

    def _on_manual_toggled(self, on: bool) -> None:
        self.manual_button.setText(
            "Continue Original Mission" if on else "Manual Target")
        if on:
            self.measure_button.setChecked(False)
        self.manual_target_mode_changed.emit(on)

    # ================================================================ feedback
    def _on_launch_state(self, state: str) -> None:
        led = {"idle": "never", "starting": "warn",
               "running": "ok", "stopping": "warn"}[state]
        self._launch_led.set_status(led)
        self.launch_button.setEnabled(state == "idle")
        self.stop_button.setEnabled(state in ("starting", "running"))

    def _on_launch_output(self, line: str) -> None:
        self._console.setText(line[-160:])

    def _on_estop_state(self, state: str) -> None:
        text = {"publishing": "safe-shutdown: publishing 'default'…",
                "confirmed": "safe-shutdown: confirmed by param_mode echo",
                "timeout": "safe-shutdown: published, flushed (no echo — check chain)",
                "sim": "safe-shutdown: simulation — ack skipped",
                "idle": ""}.get(state, "")
        self._estop_label.setText(text)
