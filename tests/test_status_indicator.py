"""Tests for the colored status indicator widget."""
from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from llama_app.ui.widgets.status_indicator import StatusIndicator, Status


@pytest.fixture(scope="module")
def qapp():
    import sys
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def test_initial_status_is_stopped(qapp):
    ind = StatusIndicator()
    assert ind.status == Status.STOPPED


def test_set_status_changes_text_and_color(qapp):
    ind = StatusIndicator()
    ind.set_status(Status.READY)
    assert ind.status == Status.READY
    assert "运行中" in ind.text() or "ready" in ind.text().lower()
