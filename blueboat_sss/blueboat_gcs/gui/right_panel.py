"""Right panel: view mode, map tools, display controls, distance tool."""

from __future__ import annotations

from typing import Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QLabel, QPushButton, QSlider,
                               QVBoxLayout, QWidget)

from ..mapping.mosaic import PRIORITY_MODES
from ..mapping.renderer import DisplaySettings, lut_names
from .widgets import CoordinateCard

#: View-mode identifiers (QStackedWidget pages in MainWindow).
VIEW_MOSAIC = "mosaic"
VIEW_WATERFALL = "waterfall"


class RightPanel(QWidget):
    """View mode, zoom/center, SonarView-like display controls, rendering
    priority, overlay clearing, and the two-click distance tool."""

    zoom_in_clicked = Signal()
    zoom_out_clicked = Signal()
    center_robot_clicked = Signal()
    measure_toggled = Signal(bool)
    view_mode_changed = Signal(str)        # VIEW_MOSAIC | VIEW_WATERFALL
    priority_changed = Signal(str)         # mosaic.PRIORITY_MODES entry
    display_changed = Signal(object)       # renderer.DisplaySettings
    clear_overlays_clicked = Signal()
    clear_sss_clicked = Signal()
    sss_opacity_changed = Signal(float)    # 0.0 .. 1.0

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ---- view mode ---------------------------------------------------------
        view_box = QGroupBox("View")
        vl = QVBoxLayout(view_box)
        self._view_combo = QComboBox()
        self._view_combo.addItem("Mosaic view", VIEW_MOSAIC)
        self._view_combo.addItem("Waterfall view (raw pings)", VIEW_WATERFALL)
        self._view_combo.currentIndexChanged.connect(
            lambda i: self.view_mode_changed.emit(self._view_combo.itemData(i)))
        vl.addWidget(self._view_combo)
        root.addWidget(view_box)

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
        clear_btn = QPushButton("Clear currently displayed data")
        clear_btn.setToolTip(
            "Clears every overlay currently shown on the map (trajectory,\n"
            "detections, measurements, pinger, planned path…).\n"
            "Hidden overlays and the SSS mosaic are preserved.\n"
            "New incoming data continues to be displayed immediately.")
        clear_btn.clicked.connect(self.clear_overlays_clicked)
        clear_sss = QPushButton("Clear SSS data")
        clear_sss.setToolTip(
            "Discards the accumulated sonar data (mosaic + waterfall)\n"
            "while preserving every other layer, the map position and the\n"
            "zoom level. New pings keep accumulating immediately.")
        clear_sss.clicked.connect(self.clear_sss_clicked)
        for b in (zoom_in, zoom_out, center, clear_btn, clear_sss):
            tl.addWidget(b)
        root.addWidget(tools)

        # ---- display controls (SonarView-like; visualization only) ------------
        root.addWidget(self._build_display_box())

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

    # ---- display controls -------------------------------------------------------
    def _build_display_box(self) -> QGroupBox:
        box = QGroupBox("Display")
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignRight)

        self._cmap = QComboBox()
        self._cmap.addItems(lut_names())
        form.addRow("Color", self._cmap)

        self._priority = QComboBox()
        for mode in PRIORITY_MODES:      # average / closest / oldest / newest
            self._priority.addItem(mode.capitalize(), mode)
        self._priority.setToolTip(
            "Which sample a mosaic cell shows where survey lines overlap\n"
            "(SonarView-like): Average, Closest (smallest slant range),\n"
            "Oldest (first pass), Newest (last pass).")
        form.addRow("Priority", self._priority)

        self._auto = QCheckBox("Auto dynamic range (2–98 %)")
        self._auto.setChecked(True)
        form.addRow(self._auto)

        self._vmin = self._slider(-90, 0, -60)
        self._vmax = self._slider(-90, 0, -10)
        self._vmin_lbl, self._vmax_lbl = QLabel(), QLabel()
        form.addRow("Min", self._wrap(self._vmin, self._vmin_lbl, "dB"))
        form.addRow("Max", self._wrap(self._vmax, self._vmax_lbl, "dB"))

        self._gamma = self._slider(30, 300, 100)     # /100 -> 0.3 … 3.0
        self._gamma_lbl = QLabel()
        form.addRow("Contrast", self._wrap(self._gamma, self._gamma_lbl))

        self._bright = self._slider(-50, 50, 0)      # /100 -> -0.5 … +0.5
        self._bright_lbl = QLabel()
        form.addRow("Brightness", self._wrap(self._bright, self._bright_lbl))

        # SSS layer transparency over the map background (compositing
        # only — the underlying data is never modified).
        self._opacity = self._slider(0, 100, 100)
        self._opacity_lbl = QLabel()
        form.addRow("SSS opacity", self._wrap(self._opacity,
                                              self._opacity_lbl))
        self._opacity.valueChanged.connect(self._emit_opacity)

        reset = QPushButton("Reset display")
        form.addRow(reset)

        # Wiring: any control change emits one immutable DisplaySettings.
        self._cmap.currentTextChanged.connect(self._emit_display)
        self._priority.currentIndexChanged.connect(
            lambda i: self.priority_changed.emit(self._priority.itemData(i)))
        self._auto.toggled.connect(self._emit_display)
        for s in (self._vmin, self._vmax, self._gamma, self._bright):
            s.valueChanged.connect(self._emit_display)
        reset.clicked.connect(self._reset_display)
        self._emit_display()
        self._emit_opacity(self._opacity.value())
        return box

    @staticmethod
    def _slider(lo: int, hi: int, val: int) -> QSlider:
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(val)
        return s

    @staticmethod
    def _wrap(slider: QSlider, label: QLabel, unit: str = "") -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        label.setMinimumWidth(44)
        label.setObjectName("valueLabel")
        lay.addWidget(slider, 1)
        lay.addWidget(label)
        label.setProperty("_unit", unit)
        return w

    def _reset_display(self) -> None:
        d = DisplaySettings()
        self._cmap.setCurrentText(d.colormap)
        self._auto.setChecked(d.auto_range)
        self._vmin.setValue(int(d.vmin_db))
        self._vmax.setValue(int(d.vmax_db))
        self._gamma.setValue(int(d.gamma * 100))
        self._bright.setValue(int(d.brightness * 100))
        self._opacity.setValue(100)
        self._emit_display()

    def _emit_opacity(self, value: int) -> None:
        self._opacity_lbl.setText(f"{value} %")
        self.sss_opacity_changed.emit(value / 100.0)

    def _emit_display(self, *_args) -> None:
        auto = self._auto.isChecked()
        for s in (self._vmin, self._vmax):
            s.setEnabled(not auto)
        vmin, vmax = self._vmin.value(), self._vmax.value()
        if vmin >= vmax:                      # keep the window well-formed
            vmax = vmin + 1
            self._vmax.blockSignals(True)
            self._vmax.setValue(vmax)
            self._vmax.blockSignals(False)
        self._vmin_lbl.setText(f"{vmin} dB")
        self._vmax_lbl.setText(f"{vmax} dB")
        gamma = self._gamma.value() / 100.0
        bright = self._bright.value() / 100.0
        self._gamma_lbl.setText(f"{gamma:.2f}")
        self._bright_lbl.setText(f"{bright:+.2f}")
        self.display_changed.emit(DisplaySettings(
            auto_range=auto, vmin_db=float(vmin), vmax_db=float(vmax),
            gamma=gamma, brightness=bright,
            colormap=self._cmap.currentText()))

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
