"""A read-only log viewer with line cap and a clear/copy toolbar."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogPanel(QWidget):
    def __init__(self, max_lines: int = 5000, parent: QWidget | None = None):
        super().__init__(parent)
        self._max_lines = max_lines
        self._view = QTextEdit()
        self._view.setReadOnly(True)
        self._view.setLineWrapMode(QTextEdit.NoWrap)
        font = QFont("Consolas")
        font.setStyleHint(QFont.Monospace)
        self._view.setFont(font)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.clear)
        self._copy_btn = QPushButton("复制选中")
        self._copy_btn.clicked.connect(self._view.copy)

        toolbar = QHBoxLayout()
        toolbar.addStretch(1)
        toolbar.addWidget(self._copy_btn)
        toolbar.addWidget(clear_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view, 1)
        layout.addLayout(toolbar)

        # Pre-define char formats for different streams
        self._fmt_stdout = QTextCharFormat()
        self._fmt_stdout.setForeground(QColor("#dddddd"))
        self._fmt_stderr = QTextCharFormat()
        self._fmt_stderr.setForeground(QColor("#ff8080"))

    def append_line(self, line: str, stream: str = "stdout") -> None:
        fmt = self._fmt_stderr if stream == "stderr" else self._fmt_stdout
        cursor = self._view.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(line + "\n", fmt)
        self._view.setTextCursor(cursor)
        self._trim()

    def clear(self) -> None:
        self._view.clear()

    def toPlainText(self) -> str:  # noqa: N802 (Qt naming)
        return self._view.toPlainText()

    def _trim(self) -> None:
        doc = self._view.document()
        while doc.blockCount() > self._max_lines:
            cursor = QTextCursor(doc.firstBlock())
            cursor.select(QTextCursor.BlockUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()  # trailing newline
