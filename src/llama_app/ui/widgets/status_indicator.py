"""A small colored circle + label for server state."""
from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class Status(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    LOADING = "loading"
    READY = "ready"
    ERROR = "error"


_COLORS = {
    Status.STOPPED: QColor("#888888"),
    Status.STARTING: QColor("#f0c040"),
    Status.LOADING: QColor("#f0a020"),
    Status.READY: QColor("#40c040"),
    Status.ERROR: QColor("#e04040"),
}

_LABELS_CN = {
    Status.STOPPED: "已停止",
    Status.STARTING: "启动中…",
    Status.LOADING: "加载模型中…",
    Status.READY: "运行中",
    Status.ERROR: "错误",
}


class _Dot(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._color = QColor("#888888")
        self.setFixedSize(QSize(14, 14))

    def set_color(self, color: QColor) -> None:
        self._color = color
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(self._color)
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 10, 10)
        super().paintEvent(ev)


class StatusIndicator(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._status = Status.STOPPED
        self._dot = _Dot()
        self._label = QLabel(_LABELS_CN[self._status])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._dot)
        layout.addWidget(self._label)

    @property
    def status(self) -> Status:
        return self._status

    def set_status(self, status: Status) -> None:
        self._status = status
        self._dot.set_color(_COLORS[status])
        self._label.setText(_LABELS_CN[status])

    def text(self) -> str:
        return self._label.text()
