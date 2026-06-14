"""Model tab: paths to llama-server.exe, model file, and mmproj."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QVBoxLayout, QWidget

from llama_app.ui.widgets.path_picker import PathPicker


class ModelTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.server_picker = PathPicker(
            "llama-server.exe", file_filter="Executables (*.exe);;All files (*)"
        )
        self.model_picker = PathPicker(
            "Model (*.gguf)", file_filter="GGUF models (*.gguf);;All files (*)"
        )
        self.mmproj_picker = PathPicker(
            "mmproj (optional)", file_filter="GGUF models (*.gguf);;All files (*)"
        )
        for p in (self.server_picker, self.model_picker, self.mmproj_picker):
            p.path_changed.connect(lambda _t: self.changed.emit())

        form = QFormLayout()
        form.addRow("llama-server 路径:", self.server_picker)
        form.addRow("模型:", self.model_picker)
        form.addRow("mmproj:", self.mmproj_picker)

        outer = QVBoxLayout(self)
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
