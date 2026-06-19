"""Monitor tab: speed test + 4 live resource plots."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from llama_app.ui.widgets.resource_plot import ResourcePlot


_DEFAULT_PROMPT = "请用三句话分别介绍北京、上海、广州三座城市。"

_RESULT_TEMPLATE = """Tokens: {tokens}
耗时: {elapsed_s:.2f} s
首 token 延迟: {first_token_ms:.0f} ms
平均速度: {tokens_per_sec:.1f} tokens/s"""


class MonitorTab(QWidget):
    start_test_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        # --- Speed test group ---
        self._prompt = QPlainTextEdit(_DEFAULT_PROMPT)
        self._prompt.setFixedHeight(80)
        self._run_btn = QPushButton(
            self.style().standardIcon(QStyle.SP_MediaPlay), "开始测试"
        )
        self._run_btn.setAccessibleName("开始速度测试")
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._result = QTextEdit()
        self._result.setReadOnly(True)
        self._result.setPlaceholderText("(尚未测试)")

        test_group = QGroupBox("速度测试")
        test_layout = QVBoxLayout(test_group)
        test_layout.addWidget(QLabel("测试 prompt:"))
        test_layout.addWidget(self._prompt)
        test_layout.addWidget(self._run_btn)
        test_layout.addWidget(QLabel("结果:"))
        test_layout.addWidget(self._result, 1)

        # --- 4 plots in 2x2 grid ---
        self._plot_cpu = ResourcePlot("CPU %", "%", color="#2563eb")
        self._plot_ram = ResourcePlot("RAM", " GB", color="#0ea5e9")
        self._plot_vram = ResourcePlot("VRAM", " GB", color="#f59e0b")
        self._plot_gpu = ResourcePlot("GPU", "%", color="#10b981")

        grid = QGridLayout()
        grid.addWidget(self._plot_cpu, 0, 0)
        grid.addWidget(self._plot_ram, 0, 1)
        grid.addWidget(self._plot_vram, 1, 0)
        grid.addWidget(self._plot_gpu, 1, 1)
        plots_group = QGroupBox("实时资源 (近 60s)")
        plots_layout = QVBoxLayout(plots_group)
        plots_layout.addLayout(grid)

        outer = QVBoxLayout(self)
        outer.addWidget(test_group)
        outer.addWidget(plots_group, 1)

    def _on_run_clicked(self) -> None:
        self.start_test_requested.emit()

    def prompt_text(self) -> str:
        return self._prompt.toPlainText()

    def set_test_pending(self) -> None:
        self._run_btn.setEnabled(False)
        self._result.setPlainText("测试中…")

    def show_test_result(self, result: dict) -> None:
        self._run_btn.setEnabled(True)
        self._result.setPlainText(_RESULT_TEMPLATE.format(**result))

    def show_test_error(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._result.setPlainText(f"测试失败: {message}")

    def update_samples(self, samples: list[dict]) -> None:
        if not samples:
            return
        latest = samples[-1]
        self._plot_cpu.push(latest.get("cpu_total"))
        self._plot_ram.push(latest.get("mem_total_gb"))
        self._plot_vram.push(latest.get("vram_gb"))
        self._plot_gpu.push(latest.get("gpu_util"))

    def set_plot_colors(self, colors: dict) -> None:
        """Repaint each resource plot with the given color palette.

        Used by MainWindow to keep pyqtgraph colors in sync with the active theme.
        """
        for plot, key in (
            (self._plot_cpu, "cpu"),
            (self._plot_ram, "ram"),
            (self._plot_vram, "vram"),
            (self._plot_gpu, "gpu"),
        ):
            color = colors.get(key)
            if color:
                plot.set_color(color)

    def set_plot_theme(self, background: str, axis: str) -> None:
        """Repaint the canvas background + axis color of all 4 plots.

        pyqtgraph ignores QSS, so the MainWindow calls this whenever the theme
        changes to keep the plots from sticking on the default black canvas.
        """
        for plot in (
            self._plot_cpu,
            self._plot_ram,
            self._plot_vram,
            self._plot_gpu,
        ):
            plot.set_background(background, axis)

    def _on_test_finished(self, result: dict) -> None:
        self.show_test_result(result)

    def _on_test_failed(self, msg: str) -> None:
        self.show_test_error(msg)
