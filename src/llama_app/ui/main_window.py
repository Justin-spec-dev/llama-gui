"""Main window for llama-gui — assembles tabs, toolbar, log panel, status bar."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QComboBox,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
)

from llama_app.core.config import Config, ConfigBuilder
from llama_app.core.presets import PresetStore
from llama_app.core.process import ServerProcess, ServerState
from llama_app.core.monitor import ResourceMonitor
from llama_app.ui.tabs.advanced_tab import AdvancedTab
from llama_app.ui.tabs.model_tab import ModelTab
from llama_app.ui.tabs.monitor_tab import MonitorTab
from llama_app.ui.tabs.network_tab import NetworkTab
from llama_app.ui.tabs.performance_tab import PerformanceTab
from llama_app.ui.tabs.presets_tab import PresetsTab
from llama_app.ui.tabs.sampling_tab import SamplingTab
from llama_app.ui.widgets.log_panel import LogPanel
from llama_app.ui.widgets.status_indicator import StatusIndicator, Status


_STYLESHEET = ""  # replaced by theme.py — keep empty


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("llama-gui")
        self.resize(1280, 860)

        # App icon
        from pathlib import Path
        icon_path = Path(__file__).parent.parent / "resources" / "icon.png"
        if icon_path.exists():
            from PySide6.QtGui import QIcon
            self.setWindowIcon(QIcon(str(icon_path)))

        self._store = PresetStore()
        self._server = ServerProcess(self)
        self._monitor: ResourceMonitor | None = None
        self._samples: list[dict] = []

        # --- Tabs ---
        self.tab_model = ModelTab()
        self.tab_perf = PerformanceTab()
        self.tab_net = NetworkTab()
        self.tab_sample = SamplingTab()
        self.tab_advanced = AdvancedTab()
        self.tab_monitor = MonitorTab()
        self.tab_presets = PresetsTab(self._store)

        self.tabs = QTabWidget()
        for w, name in [
            (self.tab_model, "模型"), (self.tab_perf, "性能"),
            (self.tab_net, "网络"), (self.tab_sample, "采样"),
            (self.tab_advanced, "高级"), (self.tab_monitor, "监控"),
            (self.tab_presets, "预设"),
        ]:
            self.tabs.addTab(w, name)

        # --- Log panel ---
        self.log = LogPanel()

        # --- Central layout ---
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.log)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        # --- Toolbar ---
        self._build_toolbar()
        # --- Status bar ---
        self._build_statusbar()
        # --- Menus / shortcuts ---
        self._build_actions()

        # --- Wire signals ---
        self._server.state_changed.connect(self._on_server_state)
        self._server.log_received.connect(self._on_log_line)
        self.tab_monitor.start_test_requested.connect(self._on_start_test)
        self.tab_presets.preset_loaded.connect(self._on_preset_loaded)
        self.tab_presets.save_requested.connect(self._on_save_preset_requested)

        self._restore_geometry()
        self._update_toolbar_state()

    # --- Assembly ---

    def _build_toolbar(self) -> None:
        tb = QToolBar("主工具栏")
        tb.setMovable(False)
        self.addToolBar(tb)
        self.act_start = QAction("▶ 启动", self)
        self.act_stop = QAction("■ 停止", self)
        self.act_restart = QAction("↻ 重启", self)
        tb.addAction(self.act_start)
        tb.addAction(self.act_stop)
        tb.addAction(self.act_restart)
        tb.addSeparator()
        self.indicator = StatusIndicator()
        tb.addWidget(self.indicator)
        tb.addSeparator()
        tb.addWidget(QLabel("  预设: "))
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(220)
        self.preset_combo.currentTextChanged.connect(self._on_combo_preset_changed)
        tb.addWidget(self.preset_combo)
        self.act_start.triggered.connect(self._on_start_clicked)
        self.act_stop.triggered.connect(self._on_stop_clicked)
        self.act_restart.triggered.connect(self._on_restart_clicked)
        self._refresh_preset_combo()

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.sb_status = QLabel("就绪")
        self.sb_cpu = QLabel("CPU —")
        self.sb_ram = QLabel("RAM —")
        self.sb_vram = QLabel("VRAM —")
        self.sb_gpu = QLabel("GPU —")
        for w in (self.sb_status, self.sb_cpu, self.sb_ram, self.sb_vram, self.sb_gpu):
            sb.addPermanentWidget(w)

    def _build_actions(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        act_save = QAction("保存当前为预设…", self)
        act_save.setShortcut(QKeySequence.Save)
        act_save.triggered.connect(self._on_save_preset_requested)
        file_menu.addAction(act_save)
        act_quit = QAction("退出", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        view_menu = self.menuBar().addMenu("视图")
        theme_menu = view_menu.addMenu("主题")
        for name, key in (("浅色", "light"), ("深色", "dark"), ("跟随系统", "auto")):
            act = QAction(name, self)
            act.triggered.connect(lambda _checked=False, k=key: self._set_theme(k))
            theme_menu.addAction(act)

        help_menu = self.menuBar().addMenu("帮助")
        act_help = QAction("快捷键", self)
        act_help.setShortcut(QKeySequence.HelpContents)
        act_help.triggered.connect(self._show_help)
        help_menu.addAction(act_help)

        self.act_stop.setShortcut(QKeySequence("Ctrl+."))
        self.act_restart.setShortcut(QKeySequence("F5"))
        self.act_start.setShortcut(QKeySequence("Ctrl+Return"))
        act_clear = QAction("清空日志", self)
        act_clear.setShortcut(QKeySequence("Ctrl+L"))
        act_clear.triggered.connect(self.log.clear)
        self.addAction(act_clear)

    # --- State ---

    def _update_toolbar_state(self) -> None:
        running = self._server.state in (ServerState.STARTING, ServerState.LOADING, ServerState.READY)
        self.act_start.setEnabled(not running)
        self.act_stop.setEnabled(running)
        self.act_restart.setEnabled(running)

    def _refresh_preset_combo(self) -> None:
        self.preset_combo.blockSignals(True)
        current = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItem("(未选择)")
        for p in self._store.list():
            self.preset_combo.addItem(p.name)
        idx = self.preset_combo.findText(current)
        if idx >= 0:
            self.preset_combo.setCurrentIndex(idx)
        self.preset_combo.blockSignals(False)
        self.tab_presets.refresh()

    def _on_combo_preset_changed(self, name: str) -> None:
        if not name or name == "(未选择)":
            return
        try:
            p = self._store.get(name)
        except KeyError:
            return
        self._apply_config_to_ui(p.config)

    def _apply_config_to_ui(self, cfg: Config) -> None:
        for w in (self.tab_model, self.tab_perf, self.tab_net, self.tab_sample, self.tab_advanced):
            w.blockSignals(True)
        try:
            self.tab_model.set_values(cfg.server_path, cfg.model_path, cfg.mmproj_path)
            self.tab_perf.set_values(_perf_dict(cfg))
            self.tab_net.set_values(_net_dict(cfg))
            self.tab_sample.set_values(_sample_dict(cfg))
            self.tab_advanced.set_values(_advanced_dict(cfg))
        finally:
            for w in (self.tab_model, self.tab_perf, self.tab_net, self.tab_sample, self.tab_advanced):
                w.blockSignals(False)

    def collect_config(self) -> Config:
        m = self.tab_model.values()
        p = self.tab_perf.values()
        n = self.tab_net.values()
        s = self.tab_sample.values()
        a = self.tab_advanced.values()
        cfg = Config(server_path=m["server_path"], model_path=m["model_path"], mmproj_path=m["mmproj_path"], **p, **n, **s, **a)
        cfg.validate()
        return cfg

    # --- Start / stop ---

    def _on_start_clicked(self) -> None:
        try:
            cfg = self.collect_config()
        except ValueError as e:
            QMessageBox.warning(self, "参数无效", str(e))
            return
        from llama_app.core.validators import validate_executable, validate_model_file, validate_mmproj_file, validate_port_available
        try:
            server = validate_executable(cfg.server_path)
            model = validate_model_file(cfg.model_path)
            if cfg.mmproj_path:
                validate_mmproj_file(cfg.mmproj_path)
        except (FileNotFoundError, ValueError) as e:
            QMessageBox.warning(self, "路径无效", str(e))
            return
        if cfg.port and not validate_port_available(cfg.host or "127.0.0.1", cfg.port):
            reply = QMessageBox.question(self, "端口占用", f"端口 {cfg.port} 似乎已被占用。继续启动？")
            if reply != QMessageBox.Yes:
                return

        args = ConfigBuilder.to_args(cfg)
        cmd_str = " ".join(f'"{a}"' if " " in a else a for a in [cfg.server_path] + args)
        self.log.append_line(f"[CMD] {cmd_str}", "stdout")

        host = cfg.host or "127.0.0.1"
        port = cfg.port or 8080
        self._server.start(
            program=str(server), arguments=args, cwd=str(model.parent),
            health_url=f"http://127.0.0.1:{port}/health",
            health_timeout_s=120,
        )
        self._update_toolbar_state()

    def _on_stop_clicked(self) -> None:
        self._server.stop()
        self._update_toolbar_state()

    def _on_restart_clicked(self) -> None:
        self._server.stop()
        self._server._proc.finished.connect(self._on_start_clicked, type=Qt.SingleShotConnection)

    # --- Server callbacks ---

    def _on_server_state(self, state: str) -> None:
        try:
            s = ServerState(state)
        except ValueError:
            return
        self.indicator.set_status({
            ServerState.STOPPED: Status.STOPPED, ServerState.STARTING: Status.STARTING,
            ServerState.LOADING: Status.LOADING, ServerState.READY: Status.READY,
            ServerState.ERROR: Status.ERROR,
        }[s])
        self.sb_status.setText(f"状态: {state}")
        if s in (ServerState.LOADING, ServerState.READY):
            self._start_monitor()
        elif s in (ServerState.STOPPED, ServerState.ERROR):
            self._stop_monitor()
        self._update_toolbar_state()

    def _on_log_line(self, line: str) -> None:
        stream = "stderr" if line.startswith("[stderr]") else "stdout"
        self.log.append_line(line, stream)

    # --- Monitor ---

    def _start_monitor(self) -> None:
        if self._monitor is not None:
            return
        self._monitor = ResourceMonitor(get_pid=self._server.pid)
        self._monitor.sample.connect(self._on_resource_sample)
        self._monitor.process_gone.connect(self._on_process_gone)
        self._monitor.start()

    def _stop_monitor(self) -> None:
        if self._monitor is None:
            return
        self._monitor.stop()
        self._monitor = None
        self.sb_cpu.setText("CPU —")
        self.sb_ram.setText("RAM —")
        self.sb_vram.setText("VRAM —")
        self.sb_gpu.setText("GPU —")

    def _on_resource_sample(self, sample: dict) -> None:
        self._samples.append(sample)
        if len(self._samples) > 3600:
            self._samples = self._samples[-3600:]
        self.sb_cpu.setText(f"CPU {sample['cpu_total']:.0f}%")
        self.sb_ram.setText(f"RAM {sample['mem_total_gb']:.1f}G")
        if sample.get("vram_gb") is not None:
            self.sb_vram.setText(f"VRAM {sample['vram_gb']:.1f}G")
            self.sb_gpu.setText(f"GPU {sample['gpu_util']:.0f}%")
        else:
            self.sb_vram.setText("VRAM N/A")
            self.sb_gpu.setText("GPU N/A")
        self.tab_monitor.update_samples(self._samples)

    def _on_process_gone(self) -> None:
        self.sb_status.setText("警告: 进程已退出")
        self._stop_monitor()

    # --- Presets ---

    def _on_preset_loaded(self, cfg: Config) -> None:
        self._apply_config_to_ui(cfg)

    def _on_save_preset_requested(self) -> None:
        name, ok = QInputDialog.getText(self, "保存预设", "预设名称:", text=self.preset_combo.currentText() or "")
        if not ok or not name.strip():
            return
        name = name.strip()
        try:
            cfg = self.collect_config()
        except ValueError as e:
            QMessageBox.warning(self, "参数无效", str(e))
            return
        try:
            self.tab_presets.save_preset(name, cfg)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", str(e))
            return
        QSettings().setValue("presets/last_loaded", name)
        self._refresh_preset_combo()

    # --- Speed test ---

    def _on_start_test(self) -> None:
        if self._server.state != ServerState.READY:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "无法测试", "请先启动 llama-server 并等待模型加载完成（状态灯变绿）")
            self.tab_monitor._run_btn.setEnabled(True)
            self.tab_monitor._result.setPlainText("(服务未就绪)")
            return
        cfg = self.collect_config()
        # Always connect via localhost — 0.0.0.0 is a bind address, not a connect address
        port = cfg.port or 8080
        from llama_app.core.speedtest import SpeedTester
        self._tester = SpeedTester(self)
        self._tester.finished.connect(self.tab_monitor._on_test_finished)
        self._tester.failed.connect(self.tab_monitor._on_test_failed)
        self._tester.run("127.0.0.1", port, cfg.api_key, self.tab_monitor._prompt.toPlainText(), max_tokens=200)

    def _set_theme(self, theme: str) -> None:
        from llama_app.ui.theme import apply_theme, save_theme
        from PySide6.QtWidgets import QApplication
        apply_theme(QApplication.instance(), theme)
        save_theme(theme)

    def _show_help(self) -> None:
        QMessageBox.information(self, "快捷键",
            "Ctrl+S   保存当前为预设\nCtrl+Enter   启动\nF5   重启\nCtrl+.   停止\nCtrl+L   清空日志\nCtrl+Q   退出\nF1   此帮助")

    def _restore_geometry(self) -> None:
        s = QSettings()
        geom = s.value("window/geometry", type=QByteArray)
        if geom:
            self.restoreGeometry(geom)

    def closeEvent(self, event) -> None:
        if self._server.is_running():
            reply = QMessageBox.question(self, "确认退出", "llama-server 仍在运行。是否停止并退出？")
            if reply != QMessageBox.Yes:
                event.ignore()
                return
            self._server.stop()
        s = QSettings()
        s.setValue("window/geometry", self.saveGeometry())
        super().closeEvent(event)


# --- Helpers ---

def _perf_dict(cfg: Config) -> dict:
    return {k: getattr(cfg, k) for k in [
        "n_gpu_layers","n_cpu_moe","ctx_size","threads","threads_batch",
        "batch_size","ubatch_size","cache_type_k","cache_type_v","flash_attn",
        "mlock","no_mmap","parallel","cont_batching",
    ]}

def _net_dict(cfg: Config) -> dict:
    return {k: getattr(cfg, k) for k in [
        "host","port","api_key","enable_ui","metrics","alias","jinja",
    ]}

def _sample_dict(cfg: Config) -> dict:
    return {k: getattr(cfg, k) for k in [
        "n_predict","temperature","top_k","top_p","min_p","repeat_penalty",
        "repeat_last_n","presence_penalty","frequency_penalty","seed",
        "reasoning","reasoning_budget",
    ]}

def _advanced_dict(cfg: Config) -> dict:
    return {k: getattr(cfg, k) for k in [
        "split_mode","tensor_split","main_gpu","lora","hf_repo","hf_file",
        "hf_token","timeout","verbose","log_verbosity","no_warmup","cache_prompt",
    ]}
