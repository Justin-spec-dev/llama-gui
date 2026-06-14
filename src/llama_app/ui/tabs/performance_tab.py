"""Performance tab: GPU layers, context, threads, batch sizes, cache types, flags."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_CACHE_TYPES = ["f16", "f32", "bf16", "q8_0", "q4_0", "q4_1", "iq4_nl", "q5_0", "q5_1"]
_FLASH_OPTS = ["auto", "on", "off"]


class PerformanceTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.ngl = QSpinBox(); self.ngl.setRange(0, 999); self.ngl.setValue(0); self.ngl.setSpecialValueText("(默认 auto)")
        self.ngl.setToolTip("GPU 加速层数 (--n-gpu-layers / -ngl)\n\n将模型的前 N 层加载到显存(VRAM)中，利用 GPU 加速推理\n0 = 纯 CPU，999 = 全部放 GPU\nllama 默认: auto（自动检测最佳层数）")
        self.ncmoe = QSpinBox(); self.ncmoe.setRange(0, 999); self.ncmoe.setValue(0); self.ncmoe.setSpecialValueText("(默认 0)")
        self.ncmoe.setToolTip("MoE 专家层保留在 CPU (--n-cpu-moe / -ncmoe)\n\nMixture of Experts 模型中，将前 N 层的专家权重保留在 CPU\n用于节省显存，仅对 MoE 模型（如 Mixtral、DeepSeek-V2）有效\nllama 默认: 0（全部放 GPU）")
        self.ctx = QSpinBox(); self.ctx.setRange(0, 1_048_576); self.ctx.setValue(0); self.ctx.setSingleStep(512); self.ctx.setSpecialValueText("(默认 读模型)")
        self.ctx.setToolTip("上下文窗口大小 (--ctx-size / -c)\n\n模型一次能处理的 token 数量上限\n越大 = 能处理更长的对话，但占用更多内存\nllama 默认: 0（使用模型训练时的上下文大小）")
        self.threads = QSpinBox(); self.threads.setRange(0, 256); self.threads.setValue(0); self.threads.setSpecialValueText("(默认 自动)")
        self.threads.setToolTip("CPU 推理线程数 (-t / --threads)\n\n用于文本生成阶段的 CPU 线程数\nllama 默认: -1（自动检测 CPU 核心数）")
        self.threads_batch = QSpinBox(); self.threads_batch.setRange(0, 256); self.threads_batch.setValue(0); self.threads_batch.setSpecialValueText("(默认 同 -t)")
        self.threads_batch.setToolTip("批处理线程数 (-tb / --threads-batch)\n\n用于 prompt 批处理阶段的 CPU 线程数\nllama 默认: 跟随 --threads 的值")
        self.batch = QSpinBox(); self.batch.setRange(0, 4096); self.batch.setValue(0); self.batch.setSpecialValueText("(默认 2048)")
        self.batch.setToolTip("逻辑批处理大小 (-b / --batch-size)\n\n一次处理的最大 token 数量\n更大的值 = 更高的吞吐量，但需要更多内存\nllama 默认: 2048")
        self.ubatch = QSpinBox(); self.ubatch.setRange(0, 4096); self.ubatch.setValue(0); self.ubatch.setSpecialValueText("(默认 512)")
        self.ubatch.setToolTip("物理微批大小 (-ub / --ubatch-size)\n\nGPU 上一次实际处理的 token 数量\n应 ≤ batch-size\nllama 默认: 512")
        self.ctk = QComboBox(); self.ctk.addItems(["(默认 f16)"] + _CACHE_TYPES); self.ctk.setCurrentText("(默认 f16)")
        self.ctk.setToolTip("K 缓存数据类型 (--cache-type-k / -ctk)\n\nKV 缓存中 Key 的数据类型\nf16=半精度, q8_0/q4_0=量化(省显存但可能降低质量)\nllama 默认: f16")
        self.ctv = QComboBox(); self.ctv.addItems(["(默认 f16)"] + _CACHE_TYPES); self.ctv.setCurrentText("(默认 f16)")
        self.ctv.setToolTip("V 缓存数据类型 (--cache-type-v / -ctv)\n\nKV 缓存中 Value 的数据类型\nf16=半精度, q8_0/q4_0=量化(省显存但可能降低质量)\nllama 默认: f16")
        self.flash = QComboBox(); self.flash.addItems(["(默认 auto)"] + _FLASH_OPTS); self.flash.setCurrentText("(默认 auto)")
        self.flash.setToolTip("Flash Attention (--flash-attn / -fa)\n\n加速注意力计算的优化技术\non=强制启用, off=禁用, auto=自动检测\nllama 默认: auto\n需要 GPU 支持，可显著提升推理速度")
        self.mlock = QCheckBox("启用 mlock（锁内存，llama 默认: 关闭）")
        self.mlock.setToolTip("锁定内存 (--mlock)\n\nllama 默认不锁内存\n勾选此框 = 强制模型保留在物理内存中")
        self.no_mmap = QCheckBox("禁用 mmap（llama 默认: 启用 mmap）")
        self.no_mmap.setToolTip("禁用内存映射 (--no-mmap)\n\nllama 默认使用 mmap 快速加载\n勾选此框 = 禁用 mmap，加载变慢但减少内存换出")
        self.parallel = QSpinBox(); self.parallel.setRange(0, 64); self.parallel.setValue(0); self.parallel.setSpecialValueText("(默认 自动)")
        self.parallel.setToolTip("并行请求槽位数 (-np / --parallel)\n\n服务器同时处理的请求数上限\nllama 默认: -1（自动根据模型和显存决定）\n更大的值允许更多用户同时使用")
        self.cont_batching = QCheckBox("禁用连续批处理（llama 默认: 启用）")
        self.cont_batching.setToolTip("禁用连续批处理 (--no-cont-batching)\n\nllama 默认启用连续批处理\n勾选此框 = 强制关闭动态批处理")

        for w in (self.ngl, self.ncmoe, self.ctx, self.threads, self.threads_batch,
                  self.batch, self.ubatch, self.parallel):
            w.valueChanged.connect(lambda _v: self.changed.emit())
        self.ctk.currentTextChanged.connect(lambda _t: self.changed.emit())
        self.ctv.currentTextChanged.connect(lambda _t: self.changed.emit())
        self.flash.currentTextChanged.connect(lambda _t: self.changed.emit())
        self.mlock.toggled.connect(lambda _v: self.changed.emit())
        self.no_mmap.toggled.connect(lambda _v: self.changed.emit())
        self.cont_batching.toggled.connect(lambda _v: self.changed.emit())

        form = QFormLayout()
        form.addRow("ngl (--n-gpu-layers):", self.ngl)
        form.addRow("n-cpu-moe (--n-cpu-moe):", self.ncmoe)
        form.addRow("ctx-size (-c):", self.ctx)
        form.addRow("threads (-t):", self.threads)
        form.addRow("threads-batch (-tb):", self.threads_batch)
        form.addRow("batch-size (-b):", self.batch)
        form.addRow("ubatch-size (-ub):", self.ubatch)
        form.addRow("cache-type-k (-ctk):", self.ctk)
        form.addRow("cache-type-v (-ctv):", self.ctv)
        form.addRow("flash-attn (-fa):", self.flash)
        form.addRow("parallel (-np):", self.parallel)
        form.addRow(self.mlock)
        form.addRow(self.no_mmap)
        form.addRow(self.cont_batching)

        outer = QVBoxLayout(self)
        outer.addLayout(form)
        outer.addStretch(1)

    def values(self) -> dict:
        return {
            "n_gpu_layers": self.ngl.value() or None,
            "n_cpu_moe": self.ncmoe.value() or None,
            "ctx_size": self.ctx.value() or None,
            "threads": self.threads.value() or None,
            "threads_batch": self.threads_batch.value() or None,
            "batch_size": self.batch.value() or None,
            "ubatch_size": self.ubatch.value() or None,
            "cache_type_k": self.ctk.currentText() if not self.ctk.currentText().startswith("(默认") else None,
            "cache_type_v": self.ctv.currentText() if not self.ctv.currentText().startswith("(默认") else None,
            "flash_attn": self.flash.currentText() if not self.flash.currentText().startswith("(默认") else None,
            "mlock": True if self.mlock.isChecked() else None,
            "no_mmap": True if self.no_mmap.isChecked() else None,
            "parallel": self.parallel.value() or None,
            "cont_batching": False if self.cont_batching.isChecked() else None,
        }

    def set_values(self, d: dict) -> None:
        def set_spin(spin: QSpinBox, key: str) -> None:
            v = d.get(key)
            spin.blockSignals(True)
            spin.setValue(v if v is not None else 0)
            spin.blockSignals(False)

        def set_combo(cb: QComboBox, key: str, default: str) -> None:
            v = d.get(key)
            cb.blockSignals(True)
            cb.setCurrentText(v if v is not None else default)
            cb.blockSignals(False)

        for spin, key in [
            (self.ngl, "n_gpu_layers"), (self.ncmoe, "n_cpu_moe"),
            (self.ctx, "ctx_size"), (self.threads, "threads"),
            (self.threads_batch, "threads_batch"), (self.batch, "batch_size"),
            (self.ubatch, "ubatch_size"), (self.parallel, "parallel"),
        ]:
            set_spin(spin, key)
        for cb, key, default in [
            (self.ctk, "cache_type_k", "(默认 f16)"), (self.ctv, "cache_type_v", "(默认 f16)"),
            (self.flash, "flash_attn", "(默认 auto)"),
        ]:
            set_combo(cb, key, default)
        for cb, key in [
            (self.mlock, "mlock"), (self.no_mmap, "no_mmap"),
            (self.cont_batching, "cont_batching"),
        ]:
            cb.blockSignals(True)
            v = d.get(key)
            if key == "cont_batching":
                cb.setChecked(v is False)
            else:
                cb.setChecked(bool(v))
            cb.blockSignals(False)
