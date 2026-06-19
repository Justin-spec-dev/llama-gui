import pytest

from llama_app.core.process import ServerState
from llama_app.ui.widgets.command_bar import CommandBar
from llama_app.ui.theme import apply_theme


@pytest.mark.parametrize(
    ("state", "start", "stop", "restart"),
    [
        (ServerState.STOPPED, True, False, False),
        (ServerState.ERROR, True, False, False),
        (ServerState.STARTING, False, True, False),
        (ServerState.LOADING, False, True, False),
        (ServerState.READY, False, True, True),
    ],
)
def test_command_bar_server_state_controls(qtbot, state, start, stop, restart):
    bar = CommandBar()
    qtbot.addWidget(bar)

    bar.set_server_state(state)

    assert bar.start_button.isEnabled() is start
    assert bar.stop_button.isEnabled() is stop
    assert bar.restart_button.isEnabled() is restart
    assert bar.status_label.property("state") == state.value
    assert bar.status_text()


def test_command_bar_ready_state_has_running_label(qtbot):
    bar = CommandBar()
    qtbot.addWidget(bar)
    bar.set_server_state(ServerState.READY)
    assert "运行" in bar.status_text()


def test_command_bar_emits_action_and_preset_signals(qtbot):
    bar = CommandBar()
    qtbot.addWidget(bar)
    bar.set_server_state(ServerState.READY)
    bar.set_presets(["默认配置", "快速"], current="快速")

    with qtbot.waitSignal(bar.stop_requested):
        bar.stop_button.click()
    with qtbot.waitSignal(bar.restart_requested):
        bar.restart_button.click()
    with qtbot.waitSignal(bar.preset_selected, check_params_cb=lambda value: value == "默认配置"):
        bar.preset_combo.setCurrentText("默认配置")

    bar.set_server_state(ServerState.STOPPED)
    with qtbot.waitSignal(bar.start_requested):
        bar.start_button.click()


def test_command_bar_summary_presets_and_dirty_marker(qtbot):
    bar = CommandBar()
    qtbot.addWidget(bar)

    bar.set_model_summary("C:/Models/model.gguf")
    bar.set_presets(["A", "B"], current="B")
    bar.set_dirty(True)

    assert bar.model_summary.text() == "C:/Models/model.gguf"
    assert bar.preset_combo.currentText() == "B"
    assert bar.dirty_label.text()

    bar.set_dirty(False)
    assert bar.dirty_label.text() == ""


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_workbench_theme_has_navigation_command_and_state_rules(qapp, theme):
    apply_theme(qapp, theme)
    qss = qapp.styleSheet()

    assert "QFrame#navigationRail" in qss
    assert "QFrame#commandBar" in qss
    assert 'QLabel#serverState[state="ready"]' in qss
    assert "QListWidget#navigationPages::item:selected" in qss
    assert ":focus" in qss
    assert ":disabled" in qss
    assert ":hover" in qss
    assert "font-size: 11.5pt" in qss
    assert "font-size: 12pt" in qss
    assert "font-size: 14pt" in qss
    assert "min-height: 30px" in qss
    assert "min-height: 32px" in qss
    assert "QPushButton[role=\"primary\"]" in qss
    assert "QListWidget#navigationPages::item" in qss


def test_application_uses_chinese_first_readable_font_stack(monkeypatch, qapp):
    import llama_app.__main__ as entrypoint

    captured = {}

    class FakeApplication:
        def __init__(self, argv):
            captured["app"] = self

        def setApplicationName(self, value):
            pass

        def setOrganizationName(self, value):
            pass

        def setFont(self, font):
            captured["font"] = font

        def setStyleSheet(self, value):
            pass

        def exec(self):
            return 0

    class FakeWindow:
        def show(self):
            pass

    monkeypatch.setattr(entrypoint, "QApplication", FakeApplication)
    monkeypatch.setattr(entrypoint, "MainWindow", FakeWindow)

    assert entrypoint.main() == 0
    font = captured["font"]
    assert font.pointSizeF() == 11.5
    assert font.families() == [
        "Microsoft YaHei UI",
        "Segoe UI Variable",
        "Segoe UI",
        "sans-serif",
    ]
