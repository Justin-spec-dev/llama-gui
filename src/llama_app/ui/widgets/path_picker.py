"""Reusable file-path input with a Browse button."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


class PathPicker(QWidget):
    path_changed = Signal(str)

    def __init__(
        self,
        label_text: str = "",
        file_filter: str = "All files (*)",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._file_filter = file_filter

        self._label = QLabel(label_text) if label_text else None
        self.line_edit = QLineEdit()
        self.line_edit.setReadOnly(True)
        self.line_edit.setPlaceholderText("(not set)")
        self._browse_btn = QPushButton("…")
        self._browse_btn.setFixedWidth(32)
        self._browse_btn.clicked.connect(self._on_browse)
        self.line_edit.textChanged.connect(self._on_text_changed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if self._label is not None:
            layout.addWidget(self._label)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self._browse_btn)

    def path(self) -> str:
        return self.line_edit.text()

    def set_path(self, path: str) -> None:
        self.line_edit.setText(path)

    def _on_text_changed(self, text: str) -> None:
        self.path_changed.emit(text)

    def _on_browse(self) -> None:
        start_dir = str(Path(self.path()).parent) if self.path() else ""
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Choose file", start_dir, self._file_filter
        )
        if chosen:
            self.set_path(chosen)
