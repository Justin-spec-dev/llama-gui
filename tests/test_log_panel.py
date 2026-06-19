"""Smoke test for the LogPanel widget."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QTextEdit

from llama_app.ui.widgets.log_panel import LogPanel


@pytest.fixture(scope="module")
def qapp():
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_log_panel_starts_empty(qapp):
    panel = LogPanel()
    assert panel.toPlainText() == ""


def test_log_panel_uses_readable_monospace_font(qapp):
    panel = LogPanel()
    view = panel.findChild(QTextEdit)

    assert view.font().pointSizeF() == 11.0
    assert view.font().families()[:2] == ["Cascadia Mono", "Consolas"]


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


def test_log_panel_filters_stderr_without_losing_records(qapp):
    panel = LogPanel()
    panel.append_line("normal", "stdout")
    panel.append_line("problem", "stderr")

    panel.set_filter("stderr")
    assert "normal" not in panel.toPlainText()
    assert "problem" in panel.toPlainText()

    panel.set_filter("all")
    assert "normal" in panel.toPlainText()
    assert "problem" in panel.toPlainText()


def test_log_panel_caps_records_while_filtered(qapp):
    panel = LogPanel(max_lines=2)
    panel.set_filter("stderr")
    panel.append_line("one", "stdout")
    panel.append_line("two", "stderr")
    panel.append_line("three", "stdout")

    panel.set_filter("all")
    assert "one" not in panel.toPlainText()
    assert "two" in panel.toPlainText()
    assert "three" in panel.toPlainText()


def test_log_panel_clear_removes_all_records(qapp):
    panel = LogPanel()
    panel.append_line("normal", "stdout")
    panel.set_filter("stderr")
    panel.clear()
    panel.set_filter("all")
    assert panel.toPlainText() == ""
