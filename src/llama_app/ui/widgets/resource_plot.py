"""A pyqtgraph-based rolling time-series plot for one metric."""
from __future__ import annotations

from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


_DEFAULT_COLOR = "#2563eb"


class ResourcePlot(QWidget):
    """A single rolling plot with a current-value label below it."""

    def __init__(
        self,
        title: str,
        unit: str,
        max_points: int = 60,
        color: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._data: deque[float | None] = deque(maxlen=max_points)
        self._unit = unit
        self._max_points = max_points
        self._color = color or _DEFAULT_COLOR

        self._plot = pg.PlotWidget(
            title=title,
            axisItems={
                "bottom": pg.AxisItem(orientation="bottom", showValues=False),
            },
        )
        self._plot.setMouseEnabled(x=False, y=False)
        # Subtle horizontal grid lines for value reference.
        self._plot.showGrid(x=False, y=True, alpha=0.25)
        self._plot.setMenuEnabled(False)
        self._plot.getPlotItem().hideButtons()
        self._curve = self._plot.plot(
            pen=pg.mkPen(color=self._color, width=2.5),
            antialias=True,
        )

        self._label = QLabel("—")
        self._label.setStyleSheet("font-size: 14px; font-weight: bold;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._plot, 1)
        layout.addWidget(self._label)

    def push(self, value: float | None) -> None:
        if value is None:
            self._data.append(None)
            self._label.setText("N/A")
        else:
            self._data.append(float(value))
            self._label.setText(f"{value:.1f}{self._unit}")
        xs: list[int] = []
        ys: list[float] = []
        last_valid: float | None = None
        for i, v in enumerate(self._data):
            if v is not None:
                xs.append(i)
                ys.append(v)
                last_valid = v
            elif last_valid is not None:
                xs.append(i)
                ys.append(last_valid)
        self._curve.setData(xs, ys)

    def set_color(self, color: str) -> None:
        """Update the curve color so the plot follows theme changes."""
        self._color = color
        self._curve.setPen(pg.mkPen(color=color, width=2))

    def set_background(self, background_hex: str, axis_hex: str | None = None) -> None:
        """Repaint the plot's canvas + axis to match the active theme.

        pyqtgraph draws with its own palette and ignores QSS, so we have to
        call ``setBackground`` and rebuild the axis pen on every theme switch.
        """
        self._plot.setBackground(background_hex)
        axis_color = axis_hex or background_hex
        pen = pg.mkPen(color=QColor(axis_color))
        for axis_name in ("bottom", "left"):
            axis = self._plot.getPlotItem().getAxis(axis_name)
            axis.setPen(pen)
            axis.setTextPen(pen)
        # Grid follows the same muted axis color.
        grid_pen = pg.mkPen(color=QColor(axis_color), style=Qt.DashLine)
        self._plot.getPlotItem().getAxis("left").setGrid(0xFF)