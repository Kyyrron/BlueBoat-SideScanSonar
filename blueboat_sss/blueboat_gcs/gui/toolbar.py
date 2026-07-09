"""Bottom toolbar: acquisition control and pipeline status."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QPushButton, QToolBar, QWidget, QSizePolicy


class AcquisitionToolbar(QToolBar):
    """START / STOP for the SSS processing pipeline.

    START launches the *processing* launch file (never sss_node.py, which
    runs on the robot) via ros/pipeline_launcher.py and, if configured,
    enables pinging + .svlog logging. STOP does the reverse.
    """

    start_clicked = Signal()
    stop_clicked = Signal()
    svlog_clicked = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__("Acquisition", parent)
        self.setMovable(False)
        self.setFloatable(False)

        self._start_btn = QPushButton("▶  START acquisition")
        self._start_btn.setObjectName("startButton")
        self._start_btn.clicked.connect(self.start_clicked)
        self.addWidget(self._start_btn)

        self._stop_btn = QPushButton("■  STOP acquisition")
        self._stop_btn.setObjectName("stopButton")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self.stop_clicked)
        self.addWidget(self._stop_btn)

        # Recording sessions — only available while the pipeline runs.
        # Ends with STOP acquisition, which finalizes the session folder.
        self._svlog_btn = QPushButton("⏺  Start recording")
        self._svlog_btn.setEnabled(False)
        self._svlog_btn.setToolTip(
            "Starts a recording session: enables .svlog logging in the\n"
            "processor and, on STOP acquisition, gathers every artifact\n"
            "(svlog, mosaic, waterfall, trajectory, detections, metadata)\n"
            "into one session folder — one experiment = one folder.")
        self._svlog_btn.clicked.connect(self._on_svlog_clicked)
        self.addWidget(self._svlog_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

        self._state_label = QLabel("pipeline: stopped")
        self._state_label.setObjectName("valueLabel")
        self.addWidget(self._state_label)

    def _on_svlog_clicked(self) -> None:
        # One session per pipeline run: re-enabled by the next 'running'.
        self._svlog_btn.setEnabled(False)
        self.svlog_clicked.emit()

    def on_recording_state(self, active: bool) -> None:
        self._svlog_btn.setText("⏺  Recording… (STOP ends the session)"
                                if active else "⏺  Start recording")

    def on_pipeline_state(self, state: str) -> None:
        self._state_label.setText(f"pipeline: {state}")
        busy = state in ("starting", "running", "stopping")
        self._start_btn.setEnabled(not busy)
        self._stop_btn.setEnabled(state in ("starting", "running"))
        self._svlog_btn.setEnabled(state == "running")
