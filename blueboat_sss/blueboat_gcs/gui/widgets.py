"""Small reusable widgets."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QPushButton,
                               QSizePolicy, QWidget)

from ..utils.geodesy import format_latlon


class CoordinateCard(QWidget):
    """Displays one point in robot-frame and GPS coordinates.

    Both rows have a copy button — during experiments coordinates are
    constantly pasted into logs / mission planners, so copying must be a
    single click (specification requirement).
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._local_txt = "—"
        self._gps_txt = "—"

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet("color:#8ab4f8; font-weight:bold;")
        grid.addWidget(title_label, 0, 0, 1, 3)

        self._local_value = QLabel("—")
        self._local_value.setObjectName("valueLabel")
        self._local_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._gps_value = QLabel("—")
        self._gps_value.setObjectName("valueLabel")
        self._gps_value.setTextInteractionFlags(Qt.TextSelectableByMouse)

        grid.addWidget(QLabel("Robot"), 1, 0)
        grid.addWidget(self._local_value, 1, 1)
        grid.addWidget(self._copy_button(lambda: self._local_txt), 1, 2)
        grid.addWidget(QLabel("GPS"), 2, 0)
        grid.addWidget(self._gps_value, 2, 1)
        grid.addWidget(self._copy_button(lambda: self._gps_txt), 2, 2)
        grid.setColumnStretch(1, 1)

    def _copy_button(self, getter) -> QPushButton:
        btn = QPushButton("⧉")
        btn.setFixedSize(24, 22)
        btn.setToolTip("Copy to clipboard")
        btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        btn.clicked.connect(
            lambda: QApplication.clipboard().setText(getter()))
        return btn

    def set_point(self, x: float, y: float,
                  gps: Optional[Tuple[float, float]]) -> None:
        self._local_txt = f"{x:.2f}, {y:.2f}"
        self._local_value.setText(f"x {x:+.2f} m   y {y:+.2f} m")
        if gps is not None:
            self._gps_txt = format_latlon(*gps)
            self._gps_value.setText(self._gps_txt)
        else:
            self._gps_txt = "—"
            self._gps_value.setText("no GPS origin yet")

    def clear(self) -> None:
        self._local_txt = self._gps_txt = "—"
        self._local_value.setText("—")
        self._gps_value.setText("—")
