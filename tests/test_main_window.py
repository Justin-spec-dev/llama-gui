from __future__ import annotations

import inspect

from PySide6.QtWidgets import (
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextEdit,
)

from llama_app.core.config import Config
from llama_app.core.presets import Preset
from llama_app.core.process import ServerState
from llama_app.ui.main_window import MainWindow
from llama_app.ui.widgets.config_page import SectionTitle


def _window(qtbot, tmp_path, monkeypatch) -> MainWindow:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_window_uses_persistent_navigation_stack(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)

    assert window.navigation.current_page() == "model"
    assert isinstance(window.page_stack, QStackedWidget)
    assert window.command_bar.isVisibleTo(window)
    assert window.current_page_key() == "model"

    window.navigation.select_page("network")
    assert window.current_page_key() == "network"


def test_window_keeps_stable_page_keys_and_scrolls_config_pages(
    qtbot, tmp_path, monkeypatch
):
    window = _window(qtbot, tmp_path, monkeypatch)

    assert window._page_keys == [
        "model",
        "performance",
        "network",
        "sampling",
        "advanced",
        "monitor",
        "presets",
    ]
    for index in range(5):
        assert isinstance(window.page_stack.widget(index), QScrollArea)
    assert window.page_stack.widget(5) is window.tab_monitor
    assert window.page_stack.widget(6) is window.tab_presets


def test_window_marks_changed_config_dirty(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)
    assert not window.is_dirty()

    window.tab_net.host.setText("0.0.0.0")

    assert window.is_dirty()
    assert window.command_bar.dirty_label.text()


def test_applying_config_does_not_mark_window_dirty(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)

    config = Config("server.exe", "model.gguf")
    window._apply_config_to_ui(config)

    assert not window.is_dirty()


def test_command_bar_reflects_every_server_state(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)

    for state in ServerState:
        window._on_server_state(state.value)
        assert window.command_bar.status_label.property("state") == state.value


def test_window_constructs_at_minimum_size(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)
    window.resize(1024, 700)
    window.show()

    assert window.minimumWidth() == 1024
    assert window.minimumHeight() == 700
    assert window.size().width() >= 1024
    assert window.page_stack.currentWidget().isVisible()


def test_main_window_uses_public_process_and_monitor_apis_only():
    source = inspect.getsource(MainWindow)

    assert "_server._" not in source
    assert "tab_monitor._" not in source
    assert ".restart(" in source
    for public_api in (
        "prompt_text()",
        "set_test_pending(",
        "show_test_result(",
        "show_test_error(",
    ):
        assert public_api in source


def test_config_pages_have_clear_sections(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)

    expected_minimums = {
        window.tab_model: 1,
        window.tab_perf: 2,
        window.tab_net: 2,
        window.tab_sample: 2,
        window.tab_advanced: 3,
    }
    for page, minimum in expected_minimums.items():
        assert len(page.findChildren(SectionTitle)) >= minimum


def test_sensitive_and_action_controls_have_accessible_names(
    qtbot, tmp_path, monkeypatch
):
    window = _window(qtbot, tmp_path, monkeypatch)

    assert window.tab_net.api_key.accessibleName()
    assert window.tab_advanced.hf_token.accessibleName()
    for picker in (
        window.tab_model.server_picker,
        window.tab_model.model_picker,
        window.tab_model.mmproj_picker,
    ):
        buttons = picker.findChildren(QPushButton)
        assert buttons and all(button.accessibleName() for button in buttons)
        assert all(button.width() >= button.sizeHint().width() for button in buttons)
    assert all(
        button.accessibleName()
        for button in window.tab_advanced.findChildren(QPushButton)
    )


def test_monitor_exposes_public_test_result_api(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)
    monitor = window.tab_monitor

    assert monitor.prompt_text()
    monitor.set_test_pending()
    monitor.show_test_result(
        {
            "tokens": 10,
            "elapsed_s": 1.0,
            "first_token_ms": 50.0,
            "tokens_per_sec": 10.5,
        }
    )
    assert "10" in monitor.findChild(QTextEdit).toPlainText()
    monitor.show_test_error("offline")
    assert "offline" in monitor.findChild(QTextEdit).toPlainText()


def test_rejected_preset_switch_keeps_dirty_changes(
    qtbot, tmp_path, monkeypatch
):
    window = _window(qtbot, tmp_path, monkeypatch)
    window._store.save(Preset.now("saved", Config("server.exe", "saved.gguf")))
    window._refresh_presets()
    window.tab_net.host.setText("0.0.0.0")
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.No)

    window.command_bar.preset_combo.setCurrentText("saved")

    assert window.is_dirty()
    assert window.tab_net.host.text() == "0.0.0.0"
    assert window.command_bar.preset_combo.currentText() == "(未选择)"


def test_successful_preset_load_clears_dirty_state(qtbot, tmp_path, monkeypatch):
    window = _window(qtbot, tmp_path, monkeypatch)
    window._store.save(Preset.now("saved", Config("server.exe", "saved.gguf")))
    window._refresh_presets()
    window.tab_net.host.setText("0.0.0.0")
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    window.command_bar.preset_combo.setCurrentText("saved")

    assert not window.is_dirty()
    assert window.tab_model.values()["model_path"] == "saved.gguf"


def test_preset_recovery_notice_is_non_modal_log_message(
    qtbot, tmp_path, monkeypatch
):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    preset_path = tmp_path / "llama-gui" / "presets.json"
    preset_path.parent.mkdir(parents=True)
    preset_path.write_text("{broken", encoding="utf-8")

    window = MainWindow()
    qtbot.addWidget(window)

    assert "[warning]" in window.log.toPlainText()
    assert window.sb_status.text() != "就绪"
