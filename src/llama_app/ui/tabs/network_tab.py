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
from llama_app.ui.widgets.config_page import SectionTitle


class NetworkTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.host = QLineEdit()
        self.host.setPlaceholderText("127.0.0.1 (llama 默认)")
        self.host.setToolTip("监听地址 (--host)\n\n服务器绑定的 IP 地址\n127.0.0.1 = 仅本机访问\n0.0.0.0 = 允许局域网内其他设备访问\nllama 默认: 127.0.0.1")
        self.port = QSpinBox(); self.port.setRange(0, 65535); self.port.setValue(0); self.port.setSpecialValueText("(默认 8080)")
        self.port.setToolTip("监听端口 (--port)\n\n服务器监听的端口号\nllama 默认: 8080")
        self.api_key = QLineEdit(); self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setAccessibleName("API 密钥")
        self.api_key.setPlaceholderText("(可选，llama 默认: 无)")
        self.api_key.setToolTip("API 密钥 (--api-key)\n\n设置后，所有 API 请求需要携带此密钥\n用于防止未授权访问，支持逗号分隔的多个密钥\nllama 默认: 无")
        self.enable_ui = QCheckBox("禁用内置 Web UI（llama 默认: 启用）")
        self.enable_ui.setToolTip("禁用内置 Web 聊天界面 (--no-ui)\n\nllama 默认启用 Web UI\n勾选此框 = 纯 API 模式，不启动 Web 界面")
        self.metrics = QCheckBox("启用 Prometheus 指标（llama 默认: 关闭）")
        self.metrics.setToolTip("Prometheus 监控指标 (--metrics)\n\n开启 /metrics 端点，暴露 Prometheus 格式的监控数据\n包括请求数、token 数、显存使用等\nllama 默认: 关闭")
        self.alias = QLineEdit()
        self.alias.setPlaceholderText("(可选，llama 默认: 无)")
        self.alias.setToolTip("模型别名 (-a / --alias)\n\n设置 API 中显示的模型名称\n支持逗号分隔的多个别名\nllama 默认: 无")
        self.jinja = QCheckBox("禁用 Jinja 模板（llama 默认: 启用）")
        self.jinja.setToolTip("禁用 Jinja 聊天模板 (--no-jinja)\n\nllama 默认使用 Jinja2 模板引擎\n勾选此框 = 改用简单文本拼接")

        self.host.textChanged.connect(lambda _t: self.changed.emit())
        self.port.valueChanged.connect(lambda _v: self.changed.emit())
        self.api_key.textChanged.connect(lambda _t: self.changed.emit())
        self.alias.textChanged.connect(lambda _t: self.changed.emit())
        self.enable_ui.toggled.connect(lambda _v: self.changed.emit())
        self.metrics.toggled.connect(lambda _v: self.changed.emit())
        self.jinja.toggled.connect(lambda _v: self.changed.emit())

        form = QFormLayout()
        form.addRow(SectionTitle("监听设置", "配置服务器绑定地址和端口"))
        form.addRow("host (--host):", self.host)
        form.addRow("port (--port):", self.port)
        form.addRow(SectionTitle("访问控制与端点", "管理认证、Web UI 和指标端点"))
        form.addRow("api-key (--api-key):", self.api_key)
        form.addRow(self.enable_ui)
        form.addRow(self.metrics)
        form.addRow(self.jinja)
        form.addRow("alias (-a):", self.alias)

        outer = QVBoxLayout(self)
        outer.setSpacing(12)
        outer.addLayout(form)
        outer.addStretch(1)

    def values(self) -> dict:
        port = self.port.value() if not self.port.specialValueText() or self.port.value() != 0 else None
        return {
            "host": self.host.text() or None,
            "port": port,
            "api_key": self.api_key.text() or None,
            "enable_ui": False if self.enable_ui.isChecked() else None,
            "metrics": True if self.metrics.isChecked() else None,
            "alias": self.alias.text() or None,
            "jinja": False if self.jinja.isChecked() else None,
        }

    def set_values(self, d: dict) -> None:
        self.host.blockSignals(True)
        self.host.setText(d.get("host") or "")
        self.host.blockSignals(False)
        self.port.blockSignals(True)
        self.port.setValue(d.get("port") or 0)
        self.port.blockSignals(False)
        self.api_key.blockSignals(True)
        self.api_key.setText(d.get("api_key") or "")
        self.api_key.blockSignals(False)
        self.alias.blockSignals(True)
        self.alias.setText(d.get("alias") or "")
        self.alias.blockSignals(False)
        for cb, key, is_disable in [
            (self.enable_ui, "enable_ui", True), (self.metrics, "metrics", False),
            (self.jinja, "jinja", True),
        ]:
            cb.blockSignals(True)
            if is_disable:
                cb.setChecked(d.get(key) is False)
            else:
                cb.setChecked(bool(d.get(key)))
            cb.blockSignals(False)
