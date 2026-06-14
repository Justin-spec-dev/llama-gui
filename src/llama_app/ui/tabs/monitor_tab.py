"""Monitor tab: speed test + 4 live resource plots."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from llama_app.core.speedtest import SpeedTester
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
        self._tester = SpeedTester(self)
        self._tester.finished.connect(self._on_test_finished)
        self._tester.failed.connect(self._on_test_failed)

        # --- Speed test group ---
        self._prompt = QPlainTextEdit(_DEFAULT_PROMPT)
        self._prompt.setFixedHeight(80)
        self._run_btn = QPushButton("▶ 开始测试")
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
        self._plot_cpu = ResourcePlot("CPU %", "%")
        self._plot_ram = ResourcePlot("RAM", " GB")
        self._plot_vram = ResourcePlot("VRAM", " GB")
        self._plot_gpu = ResourcePlot("GPU", "%")

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
        self._run_btn.setEnabled(False)
        self._result.setPlainText("测试中…")
        self.start_test_requested.emit()

    def update_samples(self, samples: list[dict]) -> None:
        if not samples:
            return
        latest = samples[-1]
        self._plot_cpu.push(latest.get("cpu_total"))
        self._plot_ram.push(latest.get("mem_total_gb"))
        self._plot_vram.push(latest.get("vram_gb"))
        self._plot_gpu.push(latest.get("gpu_util"))

    def _on_test_finished(self, result: dict) -> None:
        self._run_btn.setEnabled(True)
        self._result.setPlainText(_RESULT_TEMPLATE.format(**result))

    def _on_test_failed(self, msg: str) -> None:
        self._run_btn.setEnabled(True)
        self._result.setPlainText(f"测试失败: {msg}")
