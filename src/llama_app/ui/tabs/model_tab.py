"""Model tab: paths to llama-server.exe, model file, and mmproj."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QPushButton, QVBoxLayout, QWidget

from llama_app.ui.widgets.path_picker import PathPicker
from llama_app.ui.widgets.config_page import SectionTitle


class ModelTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.server_picker = PathPicker(
            "llama-server.exe", file_filter="Executables (*.exe);;All files (*)"
        )
        self.server_picker.setToolTip("llama-server 可执行文件路径\n\n从 llama.cpp releases 下载的 llama-server.exe")
        self.model_picker = PathPicker(
            "Model (*.gguf)", file_filter="GGUF models (*.gguf);;All files (*)"
        )
        self.model_picker.setToolTip("GGUF 格式的模型文件路径\n\n对应 -m / --model 参数\n支持 .gguf 格式的量化模型")
        self.mmproj_picker = PathPicker(
            "mmproj (optional)", file_filter="GGUF models (*.gguf);;All files (*)"
        )
        self.mmproj_picker.setToolTip("多模态投影器文件路径（可选）\n\n对应 --mmproj 参数\n多模态模型（如 LLaVA、Qwen-VL）需要此文件来处理图像")
        for p in (self.server_picker, self.model_picker, self.mmproj_picker):
            p.path_changed.connect(lambda _t: self.changed.emit())
        for picker, name in (
            (self.server_picker, "浏览 llama-server 可执行文件"),
            (self.model_picker, "浏览 GGUF 模型文件"),
            (self.mmproj_picker, "浏览多模态投影文件"),
        ):
            for button in picker.findChildren(QPushButton):
                button.setText("浏览")
                button.setAccessibleName(name)
                button.setFixedWidth(button.sizeHint().width())

        form = QFormLayout()
        form.addRow("llama-server 路径:", self.server_picker)
        form.addRow("模型:", self.model_picker)
        form.addRow("mmproj:", self.mmproj_picker)

        outer = QVBoxLayout(self)
        outer.addWidget(SectionTitle("模型与服务器", "选择运行程序、模型和可选投影文件"))
        outer.addLayout(form)
        outer.addStretch(1)

    def values(self) -> dict:
        return {
            "server_path": self.server_picker.path(),
            "model_path": self.model_picker.path(),
            "mmproj_path": self.mmproj_picker.path() or None,
        }

    def set_values(self, server: str, model: str, mmproj: str | None) -> None:
        for picker, value in [
            (self.server_picker, server),
            (self.model_picker, model),
            (self.mmproj_picker, mmproj or ""),
        ]:
            picker.blockSignals(True)
            picker.set_path(value or "")
            picker.blockSignals(False)
