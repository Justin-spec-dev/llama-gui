"""Smoke test for the LogPanel widget."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from llama_app.ui.widgets.log_panel import LogPanel


@pytest.fixture(scope="module")
def qapp():
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_log_panel_starts_empty(qapp):
    panel = LogPanel()
    assert panel.toPlainText() == ""


def test_log_panel_appends_text(qapp):
    panel = LogPanel()
    panel.append_line("hello", "stdout")
    panel.append_line("oops", "stderr")
    text = panel.toPlainText()
    assert "hello" in text
    assert "oops" in text


def test_log_panel_caps_lines(qapp):
    panel = LogPanel(max_lines=10)
    for i in range(50):
        panel.append_line(f"line {i}", "stdout")
    # Should keep only the most recent 10
    text = panel.toPlainText()
    assert "line 49" in text
    assert "line 0" not in text
    assert text.count("\n") <= 11  # 10 lines + trailing newline
