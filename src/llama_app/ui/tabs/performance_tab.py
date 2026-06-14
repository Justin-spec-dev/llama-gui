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
        self.ngl = QSpinBox(); self.ngl.setRange(0, 999); self.ngl.setValue(0)
        self.ncmoe = QSpinBox(); self.ncmoe.setRange(0, 999); self.ncmoe.setValue(0)
        self.ctx = QSpinBox(); self.ctx.setRange(128, 1_048_576); self.ctx.setValue(4096); self.ctx.setSingleStep(512)
        self.threads = QSpinBox(); self.threads.setRange(1, 256); self.threads.setValue(4)
        self.threads_batch = QSpinBox(); self.threads_batch.setRange(1, 256); self.threads_batch.setValue(0)
        self.threads_batch.setSpecialValueText("(跟随 -t)")
        self.batch = QSpinBox(); self.batch.setRange(1, 4096); self.batch.setValue(2048)
        self.ubatch = QSpinBox(); self.ubatch.setRange(1, 4096); self.ubatch.setValue(512)
        self.ctk = QComboBox(); self.ctk.addItems(_CACHE_TYPES); self.ctk.setCurrentText("f16")
        self.ctv = QComboBox(); self.ctv.addItems(_CACHE_TYPES); self.ctv.setCurrentText("f16")
        self.flash = QComboBox(); self.flash.addItems(_FLASH_OPTS); self.flash.setCurrentText("auto")
        self.mlock = QCheckBox("启用 mlock（锁内存，不交换到磁盘）")
        self.no_mmap = QCheckBox("禁用 mmap（--no-mmap）")
        self.parallel = QSpinBox(); self.parallel.setRange(1, 64); self.parallel.setValue(1)
        self.cont_batching = QCheckBox("启用连续批处理 (--cont-batching)")
        self.cont_batching.setChecked(True)

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
            "cache_type_k": self.ctk.currentText(),
            "cache_type_v": self.ctv.currentText(),
            "flash_attn": self.flash.currentText(),
            "mlock": self.mlock.isChecked(),
            "no_mmap": self.no_mmap.isChecked(),
            "parallel": self.parallel.value() or None,
            "cont_batching": self.cont_batching.isChecked(),
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
            (self.ctk, "cache_type_k", "f16"), (self.ctv, "cache_type_v", "f16"),
            (self.flash, "flash_attn", "auto"),
        ]:
            set_combo(cb, key, default)
        for cb, key in [
            (self.mlock, "mlock"), (self.no_mmap, "no_mmap"),
            (self.cont_batching, "cont_batching"),
        ]:
            cb.blockSignals(True)
            cb.setChecked(bool(d.get(key, False)))
            cb.blockSignals(False)
