"""Persistent preset, model, status, and lifecycle controls."""
from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from llama_app.core.process import ServerState


STATE_LABELS = {
    ServerState.STOPPED: "已停止",
    ServerState.STARTING: "正在启动",
    ServerState.LOADING: "正在加载",
    ServerState.READY: "运行中",
    ServerState.ERROR: "错误",
}


class CommandBar(QFrame):
    start_requested = Signal()
    stop_requested = Signal()
    restart_requested = Signal()
    preset_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("commandBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        preset_box = QVBoxLayout()
        preset_box.addWidget(QLabel("预设配置", self))
        self.preset_combo = QComboBox(self)
        self.preset_combo.setAccessibleName("预设配置")
        self.preset_combo.setToolTip("选择预设配置")
        self.preset_combo.currentTextChanged.connect(self.preset_selected)
        preset_box.addWidget(self.preset_combo)
        layout.addLayout(preset_box)

        model_box = QVBoxLayout()
        model_box.addWidget(QLabel("模型 / 服务器", self))
        self.model_summary = QLabel("未选择模型", self)
        self.model_summary.setObjectName("modelSummary")
        model_box.addWidget(self.model_summary)
        layout.addLayout(model_box, 1)

        self.status_label = QLabel(self)
        self.status_label.setObjectName("serverState")
        self.status_label.setAccessibleName("服务器状态")
        layout.addWidget(self.status_label)

        self.dirty_label = QLabel(self)
        self.dirty_label.setObjectName("dirtyState")
        layout.addWidget(self.dirty_label)

        style = self.style()
        self.start_button = self._button(
            "启动", "启动服务器", style.standardIcon(QStyle.SP_MediaPlay)
        )
        self.stop_button = self._button(
            "停止", "停止服务器", style.standardIcon(QStyle.SP_MediaStop)
        )
        self.restart_button = self._button(
            "重启", "重启服务器", style.standardIcon(QStyle.SP_BrowserReload)
        )
        self.start_button.clicked.connect(self.start_requested)
        self.stop_button.clicked.connect(self.stop_requested)
        self.restart_button.clicked.connect(self.restart_requested)

        # Promote the launch action to a solid primary button so the main
        # operation is visually distinct from the secondary stop/restart actions.
        self.start_button.setProperty("role", "primary")
        self.start_button.style().unpolish(self.start_button)
        self.start_button.style().polish(self.start_button)

        layout.addWidget(self.start_button)
        layout.addWidget(self.stop_button)
        layout.addWidget(self.restart_button)

        self.set_server_state(ServerState.STOPPED)

    def _button(self, text: str, tooltip: str, icon) -> QPushButton:
        button = QPushButton(icon, text, self)
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        return button

    def set_server_state(self, state: ServerState) -> None:
        state = ServerState(state)
        self.start_button.setEnabled(state in {ServerState.STOPPED, ServerState.ERROR})
        self.stop_button.setEnabled(
            state in {ServerState.STARTING, ServerState.LOADING, ServerState.READY}
        )
        self.restart_button.setEnabled(state is ServerState.READY)
        self.status_label.setText(f"● {STATE_LABELS[state]}")
        self.status_label.setProperty("state", state.value)
        self.setProperty("state", state.value)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_dirty(self, dirty: bool) -> None:
        self.dirty_label.setText("未保存" if dirty else "")

    def status_text(self) -> str:
        return self.status_label.text()

    def set_model_summary(self, summary: str) -> None:
        self.model_summary.setText(summary or "未选择模型")
        self.model_summary.setToolTip(summary)

    def set_presets(self, names: list[str], current: str | None = None) -> None:
        blocker = QSignalBlocker(self.preset_combo)
        self.preset_combo.clear()
        self.preset_combo.addItems(names)
        if current is not None:
            index = self.preset_combo.findText(current)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)
        del blocker

