"""Smoke test for the PathPicker widget."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QFileDialog

from llama_app.ui.widgets.path_picker import PathPicker


@pytest.fixture(scope="module")
def qapp():
    import sys

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_path_picker_starts_empty(qapp):
    pp = PathPicker("Choose file")
    assert pp.path() == ""
    assert pp.line_edit.text() == ""


def test_set_path_updates_line_edit(qapp):
    pp = PathPicker("Choose file")
    pp.set_path("C:/models/qwen.gguf")
    assert pp.path() == "C:/models/qwen.gguf"
    assert pp.line_edit.text() == "C:/models/qwen.gguf"


def test_path_picker_emits_path_changed(qapp, qtbot):
    pp = PathPicker("Choose")
    seen: list[str] = []
    pp.path_changed.connect(lambda p: seen.append(p))
    pp.set_path("x.gguf")
    assert seen == ["x.gguf"]
