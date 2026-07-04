"""Right panel: map tools (zoom, center robot) and the distance tool."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QGroupBox, QLabel, QPushButton, QVBoxLayout,
                               QWidget)

from .widgets import CoordinateCard


class RightPanel(QWidget):
    """Zoom +/-, one-shot 'center robot', and the two-click distance tool."""

    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    center_robot_clicked = Signal()
    measure_toggled = Signal(bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ---- map tools -----------------------------------------------------
        tools = QGroupBox("Map tools")
        tl = QVBoxLayout(tools)
        zoom_in = QPushButton("Zoom  +")
        zoom_out = QPushButton("Zoom  −")
        center = QPushButton("Center robot")
        center.setToolTip("Centers the view on the robot once; "
                          "the camera stays free afterwards.")
        zoom_in.clicked.connect(self.zoom_in_clicked)
        zoom_out.clicked.connect(self.zoom_out_clicked)
        center.clicked.connect(self.center_robot_clicked)
        for b in (zoom_in, zoom_out, center):
            tl.addWidget(b)
        root.addWidget(tools)

        # ---- distance tool ---------------------------------------------------
        dist = QGroupBox("Distance tool")
        dl = QVBoxLayout(dist)
        self._measure_btn = QPushButton("Measure distance")
        self._measure_btn.setCheckable(True)
        self._measure_btn.toggled.connect(self._on_measure_toggled)
        dl.addWidget(self._measure_btn)

        self._hint = QLabel("Enable, then click two points on the map.")
        self._hint.setWordWrap(True)
        self._hint.setStyleSheet("color:#8b95a1;")
        dl.addWidget(self._hint)

        self._distance_label = QLabel("—")
        self._distance_label.setObjectName("sectionValue")
        dl.addWidget(self._distance_label)

        self.point_a = CoordinateCard("Point A")
        self.point_b = CoordinateCard("Point B")
        dl.addWidget(self.point_a)
        dl.addWidget(self.point_b)
        root.addWidget(dist)

        root.addStretch(1)

    # ---- slots -----------------------------------------------------------------
    def _on_measure_toggled(self, on: bool) -> None:
        self._hint.setText("Click the first point…" if on
                           else "Enable, then click two points on the map.")
        if on:
            self._distance_label.setText("—")
            self.point_a.clear()
            self.point_b.clear()
        self.measure_toggled.emit(on)

    def set_measure_active(self, on: bool) -> None:
        self._measure_btn.setChecked(on)

    def on_first_point(self) -> None:
        self._hint.setText("Click the second point…")

    def show_distance(self, distance_m: float) -> None:
        self._distance_label.setText(f"Distance: {distance_m:.2f} m")
        self._hint.setText("Click again to start a new measurement.")
