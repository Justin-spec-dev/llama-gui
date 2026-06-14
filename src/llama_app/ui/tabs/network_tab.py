"""Network tab: host, port, api-key, Web UI, metrics, alias, jinja."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class NetworkTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.host = QLineEdit("127.0.0.1")
        self.port = QSpinBox(); self.port.setRange(1, 65535); self.port.setValue(8080)
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("(可选)")
        self.enable_ui = QCheckBox("启用内置 Web UI (--ui)")
        self.enable_ui.setChecked(True)
        self.metrics = QCheckBox("暴露 Prometheus 指标 (--metrics)")
        self.alias = QLineEdit()
        self.alias.setPlaceholderText("(可选) API 显示的模型名")
        self.jinja = QCheckBox("使用 Jinja 聊天模板 (--jinja)")
        self.jinja.setChecked(True)

        self.host.textChanged.connect(lambda _t: self.changed.emit())
        self.port.valueChanged.connect(lambda _v: self.changed.emit())
        self.api_key.textChanged.connect(lambda _t: self.changed.emit())
        self.alias.textChanged.connect(lambda _t: self.changed.emit())
        self.enable_ui.toggled.connect(lambda _v: self.changed.emit())
        self.metrics.toggled.connect(lambda _v: self.changed.emit())
        self.jinja.toggled.connect(lambda _v: self.changed.emit())

        form = QFormLayout()
        form.addRow("host (--host):", self.host)
        form.addRow("port (--port):", self.port)
        form.addRow("api-key (--api-key):", self.api_key)
        form.addRow(self.enable_ui)
        form.addRow(self.metrics)
        form.addRow(self.jinja)
        form.addRow("alias (-a):", self.alias)

        outer = QVBoxLayout(self)
        outer.addLayout(form)
        outer.addStretch(1)

    def values(self) -> dict:
        return {
            "host": self.host.text() or None,
            "port": self.port.value(),
            "api_key": self.api_key.text() or None,
            "enable_ui": self.enable_ui.isChecked(),
            "metrics": self.metrics.isChecked(),
            "alias": self.alias.text() or None,
            "jinja": self.jinja.isChecked(),
        }

    def set_values(self, d: dict) -> None:
        for w, key, default in [
            (self.host, "host", "127.0.0.1"), (self.api_key, "api_key", ""),
            (self.alias, "alias", ""),
        ]:
            w.blockSignals(True)
            w.setText(d.get(key) or default)
            w.blockSignals(False)
        self.port.blockSignals(True)
        self.port.setValue(d.get("port") or 8080)
        self.port.blockSignals(False)
        for cb, key, default in [
            (self.enable_ui, "enable_ui", True), (self.metrics, "metrics", False),
            (self.jinja, "jinja", True),
        ]:
            cb.blockSignals(True)
            cb.setChecked(bool(d.get(key, default)))
            cb.blockSignals(False)
