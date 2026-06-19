"""Shared, record-backed log drawer with filtering controls."""
from __future__ import annotations

from collections import deque

from PySide6.QtGui import QColor, QPalette, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    def __init__(self, max_lines: int = 5000, parent: QWidget | None = None):
        super().__init__(parent)
        self._records: deque[tuple[str, str]] = deque(maxlen=max_lines)
        self._filter = "all"

        self._view = QTextEdit(self)
        self._view.setReadOnly(True)
        self._view.setLineWrapMode(QTextEdit.NoWrap)
        self._view.setAccessibleName("运行日志")

        self.filter_combo = QComboBox(self)
        self.filter_combo.addItem("全部", "all")
        self.filter_combo.addItem("标准输出", "stdout")
        self.filter_combo.addItem("标准错误", "stderr")
        self.filter_combo.setAccessibleName("日志流筛选")
        self.filter_combo.currentIndexChanged.connect(self._filter_changed)

        self.auto_scroll = QCheckBox("自动滚动", self)
        self.auto_scroll.setChecked(True)
        self.auto_scroll.setAccessibleName("自动滚动日志")

        self._copy_btn = QPushButton("复制", self)
        self._copy_btn.setAccessibleName("复制日志")
        self._copy_btn.clicked.connect(self._copy)
        self._clear_btn = QPushButton("清空", self)
        self._clear_btn.setAccessibleName("清空日志")
        self._clear_btn.clicked.connect(self.clear)

        header = QHBoxLayout()
        header.addWidget(QLabel("运行日志", self))
        header.addWidget(QLabel("日志流", self))
        header.addWidget(self.filter_combo)
        header.addWidget(self.auto_scroll)
        header.addStretch(1)
        header.addWidget(self._copy_btn)
        header.addWidget(self._clear_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self._view, 1)

        self._create_formats_from_palette()

    def append_line(self, line: str, stream: str = "stdout") -> None:
        if stream not in {"stdout", "stderr"}:
            raise ValueError(stream)
        evicted = len(self._records) == self._records.maxlen
        self._records.append((line, stream))
        if evicted:
            self._rebuild()
        elif self._filter in {"all", stream}:
            self._append_visible(line, stream)

    def set_filter(self, stream: str) -> None:
        if stream not in {"all", "stdout", "stderr"}:
            raise ValueError(stream)
        self._filter = stream
        index = self.filter_combo.findData(stream)
        self.filter_combo.blockSignals(True)
        self.filter_combo.setCurrentIndex(index)
        self.filter_combo.blockSignals(False)
        self._rebuild()

    def clear(self) -> None:
        self._records.clear()
        self._view.clear()

    def toPlainText(self) -> str:  # noqa: N802 (Qt naming)
        return self._view.toPlainText()

    def refresh_theme(self) -> None:
        self._create_formats_from_palette()
        self._rebuild()

    def _filter_changed(self, index: int) -> None:
        self.set_filter(str(self.filter_combo.itemData(index)))

    def _copy(self) -> None:
        cursor = self._view.textCursor()
        if not cursor.hasSelection():
            self._view.selectAll()
        self._view.copy()
        self._view.setTextCursor(cursor)

    def _append_visible(self, line: str, stream: str) -> None:
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.End)
        fmt = self._fmt_stderr if stream == "stderr" else self._fmt_stdout
        cursor.insertText(line + "\n", fmt)
        if self.auto_scroll.isChecked():
            self._view.setTextCursor(cursor)
            self._view.ensureCursorVisible()

    def _rebuild(self) -> None:
        self._view.clear()
        for line, stream in self._records:
            if self._filter in {"all", stream}:
                self._append_visible(line, stream)

    def _create_formats_from_palette(self) -> None:
        text_color = self._view.palette().color(QPalette.ColorRole.Text)
        stderr_color = QColor("#ff6666" if text_color.lightness() > 128 else "#cc0000")
        self._fmt_stdout = QTextCharFormat()
        self._fmt_stdout.setForeground(text_color)
        self._fmt_stderr = QTextCharFormat()
        self._fmt_stderr.setForeground(stderr_color)
