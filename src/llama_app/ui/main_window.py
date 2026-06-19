"""Composition root for the persistent Navigation Workbench."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSettings, Qt
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from llama_app.core.command import format_display_command
from llama_app.core.config import Config, ConfigBuilder
from llama_app.core.monitor import ResourceMonitor
from llama_app.core.presets import PresetStore
from llama_app.core.process import LaunchSpec, ServerProcess, ServerState
from llama_app.core.speedtest import SpeedTester
from llama_app.core.validators import (
    validate_executable,
    validate_mmproj_file,
    validate_model_file,
    validate_port_available,
)
from llama_app.ui.tabs.advanced_tab import AdvancedTab
from llama_app.ui.tabs.model_tab import ModelTab
from llama_app.ui.tabs.monitor_tab import MonitorTab
from llama_app.ui.tabs.network_tab import NetworkTab
from llama_app.ui.tabs.performance_tab import PerformanceTab
from llama_app.ui.tabs.presets_tab import PresetsTab
from llama_app.ui.tabs.sampling_tab import SamplingTab
from llama_app.ui.widgets.command_bar import CommandBar
from llama_app.ui.widgets.config_page import make_scroll_page
from llama_app.ui.widgets.log_panel import LogPanel
from llama_app.ui.widgets.navigation_rail import NavigationRail


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("llama-gui")
        self.setMinimumSize(1024, 700)
        self.resize(1280, 860)

        icon_path = Path(__file__).parent.parent / "resources" / "icon.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._store = PresetStore()
        self._server = ServerProcess(self)
        self._tester = SpeedTester(self)
        self._monitor: ResourceMonitor | None = None
        self._samples: list[dict] = []
        self._dirty = False
        self._applying_config = False
        self._current_preset: str | None = None

        self.tab_model = ModelTab()
        self.tab_perf = PerformanceTab()
        self.tab_net = NetworkTab()
        self.tab_sample = SamplingTab()
        self.tab_advanced = AdvancedTab()
        self.tab_monitor = MonitorTab()
        self.tab_presets = PresetsTab(self._store)
        self._pages = {
            "model": self.tab_model,
            "performance": self.tab_perf,
            "network": self.tab_net,
            "sampling": self.tab_sample,
            "advanced": self.tab_advanced,
            "monitor": self.tab_monitor,
            "presets": self.tab_presets,
        }

        self.command_bar = CommandBar()
        self.navigation = NavigationRail()
        self.page_stack = QStackedWidget()
        self._page_keys: list[str] = []
        for key, page in self._pages.items():
            self._page_keys.append(key)
            displayed = page if key in {"monitor", "presets"} else make_scroll_page(page)
            self.page_stack.addWidget(displayed)

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)
        workspace_layout.addWidget(self.navigation)
        workspace_layout.addWidget(self.page_stack, 1)

        upper = QWidget()
        upper_layout = QVBoxLayout(upper)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(0)
        upper_layout.addWidget(self.command_bar)
        upper_layout.addWidget(workspace, 1)

        self.log = LogPanel()
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.addWidget(upper)
        self.splitter.addWidget(self.log)
        self.splitter.setStretchFactor(0, 3)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([650, 210])
        self.setCentralWidget(self.splitter)

        self._build_statusbar()
        self._build_actions()
        self._wire_signals()
        self._refresh_presets()
        self._restore_last_preset()
        self._restore_geometry()
        self._on_server_state(self._server.state.value)
        self._show_recovery_notice()

    def _build_statusbar(self) -> None:
        bar = QStatusBar(self)
        self.setStatusBar(bar)
        self.sb_status = QLabel("就绪", self)
        self.sb_runtime = QLabel("已停止", self)
        bar.addWidget(self.sb_status, 1)
        bar.addPermanentWidget(self.sb_runtime)

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        save_action = QAction("保存当前为预设", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._on_save_preset_requested)
        file_menu.addAction(save_action)
        quit_action = QAction("退出", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        theme_menu = self.menuBar().addMenu("视图").addMenu("主题")
        for label, key in (("浅色", "light"), ("深色", "dark"), ("跟随系统", "auto")):
            action = QAction(label, self)
            action.triggered.connect(lambda _checked=False, value=key: self._set_theme(value))
            theme_menu.addAction(action)

        help_action = QAction("快捷键", self)
        help_action.setShortcut(QKeySequence.HelpContents)
        help_action.triggered.connect(self._show_help)
        self.menuBar().addMenu("帮助").addAction(help_action)

        shortcuts = (
            ("启动服务器", "Ctrl+Return", self._on_start_clicked),
            ("停止服务器", "Ctrl+.", self._on_stop_clicked),
            ("重启服务器", "F5", self._on_restart_clicked),
            ("清空日志", "Ctrl+L", self.log.clear),
        )
        for label, sequence, handler in shortcuts:
            action = QAction(label, self)
            action.setShortcut(QKeySequence(sequence))
            action.triggered.connect(handler)
            self.addAction(action)

    def _wire_signals(self) -> None:
        self.navigation.page_selected.connect(self._select_page)
        self.command_bar.start_requested.connect(self._on_start_clicked)
        self.command_bar.stop_requested.connect(self._on_stop_clicked)
        self.command_bar.restart_requested.connect(self._on_restart_clicked)
        self.command_bar.preset_selected.connect(self._on_combo_preset_changed)

        self._server.state_changed.connect(self._on_server_state)
        self._server.log_received.connect(self._on_log_line)
        self._server.pid_changed.connect(self._on_pid_changed)
        self._tester.finished.connect(self._on_test_finished)
        self._tester.failed.connect(self._on_test_failed)
        self.tab_monitor.start_test_requested.connect(self._on_start_test)
        self.tab_presets.preset_loaded.connect(self._on_preset_loaded)
        self.tab_presets.save_requested.connect(self._on_save_preset_requested)
        for page in (
            self.tab_model,
            self.tab_perf,
            self.tab_net,
            self.tab_sample,
            self.tab_advanced,
        ):
            page.changed.connect(self._mark_dirty)

    def _select_page(self, key: str) -> None:
        try:
            self.page_stack.setCurrentIndex(self._page_keys.index(key))
        except ValueError:
            raise KeyError(key) from None

    def current_page_key(self) -> str:
        return self._page_keys[self.page_stack.currentIndex()]

    def is_dirty(self) -> bool:
        return self._dirty

    def _mark_dirty(self) -> None:
        if self._applying_config:
            return
        self._dirty = True
        self.command_bar.set_dirty(True)
        self.command_bar.set_model_summary(self.tab_model.values()["model_path"])

    def _clear_dirty(self) -> None:
        self._dirty = False
        self.command_bar.set_dirty(False)

    def _confirm_discard_changes(self) -> bool:
        if not self._dirty:
            return True
        return QMessageBox.question(
            self,
            "未保存的更改",
            "当前配置尚未保存。要放弃这些更改吗？",
        ) == QMessageBox.Yes

    def _refresh_presets(self) -> None:
        names = ["(未选择)", *(preset.name for preset in self._store.list())]
        current = self._current_preset or "(未选择)"
        self.command_bar.set_presets(names, current)
        self.tab_presets.refresh()

    def _on_combo_preset_changed(self, name: str) -> None:
        if not name or name == "(未选择)" or name == self._current_preset:
            return
        if not self._confirm_discard_changes():
            self.command_bar.set_presets(
                ["(未选择)", *(p.name for p in self._store.list())],
                self._current_preset or "(未选择)",
            )
            return
        try:
            config = self._store.get(name).config
        except KeyError:
            return
        self._load_preset(name, config)

    def _on_preset_loaded(self, config: Config) -> None:
        if not self._confirm_discard_changes():
            return
        self._load_preset(self.tab_presets.selected_name(), config)

    def _load_preset(self, name: str | None, config: Config) -> None:
        self._apply_config_to_ui(config)
        self._current_preset = name
        if name:
            QSettings().setValue("presets/last_loaded", name)
        self._clear_dirty()
        self._refresh_presets()

    def _restore_last_preset(self) -> None:
        name = QSettings().value("presets/last_loaded", "", type=str)
        if not name:
            return
        try:
            config = self._store.get(name).config
        except KeyError:
            return
        self._load_preset(name, config)

    def _apply_config_to_ui(self, config: Config) -> None:
        self._applying_config = True
        try:
            self.tab_model.set_values(
                config.server_path, config.model_path, config.mmproj_path
            )
            self.tab_perf.set_values(_perf_dict(config))
            self.tab_net.set_values(_net_dict(config))
            self.tab_sample.set_values(_sample_dict(config))
            self.tab_advanced.set_values(_advanced_dict(config))
            self.command_bar.set_model_summary(config.model_path)
        finally:
            self._applying_config = False

    def collect_config(self) -> Config:
        model = self.tab_model.values()
        config = Config(
            server_path=model["server_path"],
            model_path=model["model_path"],
            mmproj_path=model["mmproj_path"],
            **self.tab_perf.values(),
            **self.tab_net.values(),
            **self.tab_sample.values(),
            **self.tab_advanced.values(),
        )
        config.validate()
        return config

    def _build_launch_spec(self, *, check_port: bool = True) -> LaunchSpec:
        config = self.collect_config()
        server = validate_executable(config.server_path)
        model = validate_model_file(config.model_path)
        if config.mmproj_path:
            validate_mmproj_file(config.mmproj_path)
        port = config.port or 8080
        if check_port and not validate_port_available(config.host or "127.0.0.1", port):
            raise ValueError(f"端口 {port} 已被占用")
        arguments = ConfigBuilder.to_args(config)
        return LaunchSpec(
            program=str(server),
            arguments=tuple(arguments),
            cwd=str(model.parent),
            health_url=f"http://127.0.0.1:{port}/health",
            health_timeout_s=120,
        )

    def _show_validation_error(self, error: Exception) -> None:
        QMessageBox.warning(self, "无法启动服务器", str(error))

    def _log_command(self, spec: LaunchSpec) -> None:
        self.log.append_line(
            f"[CMD] {format_display_command(spec.program, spec.arguments)}", "stdout"
        )

    def _on_start_clicked(self) -> None:
        try:
            spec = self._build_launch_spec(check_port=True)
        except (ValueError, FileNotFoundError) as error:
            self._show_validation_error(error)
            return
        self._log_command(spec)
        try:
            self._server.start(
                spec.program,
                list(spec.arguments),
                cwd=spec.cwd,
                health_url=spec.health_url,
                health_timeout_s=spec.health_timeout_s,
            )
        except RuntimeError as error:
            self._show_validation_error(error)

    def _on_stop_clicked(self) -> None:
        self._server.stop()

    def _on_restart_clicked(self) -> None:
        try:
            spec = self._build_launch_spec(check_port=False)
        except (ValueError, FileNotFoundError) as error:
            self._show_validation_error(error)
            return
        self._log_command(spec)
        self._server.restart(
            spec.program,
            list(spec.arguments),
            cwd=spec.cwd,
            health_url=spec.health_url,
            health_timeout_s=spec.health_timeout_s,
        )

    def _on_server_state(self, state: str) -> None:
        try:
            server_state = ServerState(state)
        except ValueError:
            return
        self.command_bar.set_server_state(server_state)
        self.sb_runtime.setText(self.command_bar.status_text())
        if server_state in {ServerState.LOADING, ServerState.READY}:
            self._start_monitor()
        elif server_state in {ServerState.STOPPED, ServerState.ERROR}:
            self._stop_monitor()

    def _on_log_line(self, line: str) -> None:
        stream = "stderr" if line.startswith("[stderr]") else "stdout"
        self.log.append_line(line, stream)

    def _on_pid_changed(self, pid: int) -> None:
        if pid > 0 and self._server.state in {ServerState.LOADING, ServerState.READY}:
            self._start_monitor()
        elif pid <= 0:
            self._stop_monitor()

    def _start_monitor(self) -> None:
        if self._monitor is not None or self._server.pid() is None:
            return
        self._monitor = ResourceMonitor(get_pid=self._server.pid)
        self._monitor.sample.connect(self._on_resource_sample)
        self._monitor.process_gone.connect(self._on_process_gone)
        self._monitor.start()

    def _stop_monitor(self) -> None:
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None
        self.navigation.update_resources(0, 0, None, None)

    def _on_resource_sample(self, sample: dict) -> None:
        self._samples.append(sample)
        if len(self._samples) > 3600:
            del self._samples[:-3600]
        cpu = sample.get("cpu_total", 0)
        ram = sample.get("mem_total_gb", 0)
        vram = sample.get("vram_gb")
        gpu = sample.get("gpu_util")
        self.navigation.update_resources(cpu, ram, vram, gpu)
        self.tab_monitor.update_samples(self._samples)

    def _on_process_gone(self) -> None:
        self.sb_status.setText("警告：服务器进程已退出")
        self._stop_monitor()

    def _on_save_preset_requested(self) -> None:
        initial = self._current_preset or ""
        name, accepted = QInputDialog.getText(
            self, "保存预设", "预设名称:", text=initial
        )
        if not accepted or not name.strip():
            return
        name = name.strip()
        try:
            config = self.collect_config()
            self.tab_presets.save_preset(name, config)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "保存失败", str(error))
            return
        self._current_preset = name
        QSettings().setValue("presets/last_loaded", name)
        self._clear_dirty()
        self._refresh_presets()

    def _on_start_test(self) -> None:
        if self._server.state is not ServerState.READY:
            message = "请先启动服务器并等待模型加载完成。"
            self.tab_monitor.show_test_error(message)
            QMessageBox.warning(self, "无法测试", message)
            return
        try:
            config = self.collect_config()
        except ValueError as error:
            self.tab_monitor.show_test_error(str(error))
            return
        self.tab_monitor.set_test_pending()
        self._tester.run(
            "127.0.0.1",
            config.port or 8080,
            config.api_key,
            self.tab_monitor.prompt_text(),
            max_tokens=200,
        )

    def _on_test_finished(self, result: dict) -> None:
        self.tab_monitor.show_test_result(result)

    def _on_test_failed(self, message: str) -> None:
        self.tab_monitor.show_test_error(message)

    def _show_recovery_notice(self) -> None:
        if not self._store.recovery_notice:
            return
        message = self._store.recovery_notice
        self.log.append_line(f"[warning] {message}", "stderr")
        self.sb_status.setText(message)

    def _set_theme(self, theme: str) -> None:
        from llama_app.ui.theme import apply_theme, save_theme

        apply_theme(QApplication.instance(), theme)
        save_theme(theme)
        self.log.refresh_theme()

    def _show_help(self) -> None:
        QMessageBox.information(
            self,
            "快捷键",
            "Ctrl+S  保存预设\nCtrl+Enter  启动\nF5  重启\n"
            "Ctrl+.  停止\nCtrl+L  清空日志\nCtrl+Q  退出\nF1  帮助",
        )

    def _restore_geometry(self) -> None:
        geometry = QSettings().value("window/geometry", type=QByteArray)
        if geometry:
            self.restoreGeometry(geometry)

    def closeEvent(self, event) -> None:
        if self._server.is_running():
            answer = QMessageBox.question(
                self, "确认退出", "llama-server 仍在运行。是否停止并退出？"
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self._server.stop()
        QSettings().setValue("window/geometry", self.saveGeometry())
        super().closeEvent(event)


def _perf_dict(config: Config) -> dict:
    return {key: getattr(config, key) for key in (
        "n_gpu_layers", "n_cpu_moe", "ctx_size", "threads", "threads_batch",
        "batch_size", "ubatch_size", "cache_type_k", "cache_type_v", "flash_attn",
        "mlock", "no_mmap", "parallel", "cont_batching",
    )}


def _net_dict(config: Config) -> dict:
    return {key: getattr(config, key) for key in (
        "host", "port", "api_key", "enable_ui", "metrics", "alias", "jinja",
    )}


def _sample_dict(config: Config) -> dict:
    return {key: getattr(config, key) for key in (
        "n_predict", "temperature", "top_k", "top_p", "min_p", "repeat_penalty",
        "repeat_last_n", "presence_penalty", "frequency_penalty", "seed", "reasoning",
        "reasoning_budget",
    )}


def _advanced_dict(config: Config) -> dict:
    return {key: getattr(config, key) for key in (
        "split_mode", "tensor_split", "main_gpu", "lora", "hf_repo", "hf_file",
        "hf_token", "timeout", "verbose", "log_verbosity", "no_warmup", "cache_prompt",
    )}
