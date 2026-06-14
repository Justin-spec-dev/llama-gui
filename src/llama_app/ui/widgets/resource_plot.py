"""A pyqtgraph-based rolling time-series plot for one metric."""
from __future__ import annotations

from collections import deque

import pyqtgraph as pg
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResourcePlot(QWidget):
    """A single rolling plot with a current-value label below it."""

    def __init__(
        self,
        title: str,
        unit: str,
        max_points: int = 60,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._data: deque[float | None] = deque(maxlen=max_points)
        self._unit = unit
        self._max_points = max_points

        self._plot = pg.PlotWidget(title=title)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.showGrid(x=False, y=True, alpha=0.3)
        self._curve = self._plot.plot(pen=pg.mkPen(width=2))

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
