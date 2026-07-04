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

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.addWidget(spacer)

        self._state_label = QLabel("pipeline: stopped")
        self._state_label.setObjectName("valueLabel")
        self.addWidget(self._state_label)

    def on_pipeline_state(self, state: str) -> None:
        self._state_label.setText(f"pipeline: {state}")
        running_ish = state in ("starting", "running")
        self._start_btn.setEnabled(not running_ish)
        self._stop_btn.setEnabled(running_ish)
