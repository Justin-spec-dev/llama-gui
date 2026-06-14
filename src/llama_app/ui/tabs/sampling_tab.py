"""Sampling tab: temperature, top-k/p, penalties, seed, reasoning."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_REASONING_OPTS = ["auto", "on", "off"]


class SamplingTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.n_predict = QSpinBox(); self.n_predict.setRange(-1, 1_000_000); self.n_predict.setValue(-1)
        self.n_predict.setSpecialValueText("无限 (-1)")
        self.temp = QDoubleSpinBox(); self.temp.setRange(0.0, 5.0); self.temp.setSingleStep(0.05); self.temp.setValue(0.8)
        self.top_k = QSpinBox(); self.top_k.setRange(0, 200); self.top_k.setValue(40)
        self.top_p = QDoubleSpinBox(); self.top_p.setRange(0.0, 1.0); self.top_p.setSingleStep(0.01); self.top_p.setValue(0.95)
        self.min_p = QDoubleSpinBox(); self.min_p.setRange(0.0, 1.0); self.min_p.setSingleStep(0.01); self.min_p.setValue(0.05)
        self.repeat_penalty = QDoubleSpinBox(); self.repeat_penalty.setRange(0.5, 2.0); self.repeat_penalty.setSingleStep(0.05); self.repeat_penalty.setValue(1.0)
        self.repeat_last_n = QSpinBox(); self.repeat_last_n.setRange(-1, 2048); self.repeat_last_n.setValue(64)
        self.repeat_last_n.setSpecialValueText("禁用 (0)")
        self.presence = QDoubleSpinBox(); self.presence.setRange(-2.0, 2.0); self.presence.setSingleStep(0.05); self.presence.setValue(0.0)
        self.frequency = QDoubleSpinBox(); self.frequency.setRange(-2.0, 2.0); self.frequency.setSingleStep(0.05); self.frequency.setValue(0.0)
        self.seed = QSpinBox(); self.seed.setRange(-1, 2**31 - 1); self.seed.setValue(-1)
        self.seed.setSpecialValueText("随机 (-1)")
        self.reasoning = QComboBox(); self.reasoning.addItems(_REASONING_OPTS); self.reasoning.setCurrentText("auto")
        self.reasoning_budget = QSpinBox(); self.reasoning_budget.setRange(-1, 1_000_000); self.reasoning_budget.setValue(-1)
        self.reasoning_budget.setSpecialValueText("无限 (-1)")

        for w in (self.n_predict, self.top_k, self.repeat_last_n, self.seed,
                  self.reasoning_budget):
            w.valueChanged.connect(lambda _v: self.changed.emit())
        for w in (self.temp, self.top_p, self.min_p, self.repeat_penalty,
                  self.presence, self.frequency):
            w.valueChanged.connect(lambda _v: self.changed.emit())
        self.reasoning.currentTextChanged.connect(lambda _t: self.changed.emit())

        form = QFormLayout()
        form.addRow("n-predict (-n):", self.n_predict)
        form.addRow("temperature (--temp):", self.temp)
        form.addRow("top-k (--top-k):", self.top_k)
        form.addRow("top-p (--top-p):", self.top_p)
        form.addRow("min-p (--min-p):", self.min_p)
        form.addRow("repeat-penalty:", self.repeat_penalty)
        form.addRow("repeat-last-n:", self.repeat_last_n)
        form.addRow("presence-penalty:", self.presence)
        form.addRow("frequency-penalty:", self.frequency)
        form.addRow("seed (-s):", self.seed)
        form.addRow("reasoning (--reasoning):", self.reasoning)
        form.addRow("reasoning-budget:", self.reasoning_budget)

        outer = QVBoxLayout(self)
        outer.addLayout(form)
        outer.addStretch(1)

    def values(self) -> dict:
        return {
            "n_predict": self.n_predict.value(),
            "temperature": self.temp.value(),
            "top_k": self.top_k.value(),
            "top_p": self.top_p.value(),
            "min_p": self.min_p.value(),
            "repeat_penalty": self.repeat_penalty.value(),
            "repeat_last_n": self.repeat_last_n.value(),
            "presence_penalty": self.presence.value(),
            "frequency_penalty": self.frequency.value(),
            "seed": self.seed.value(),
            "reasoning": self.reasoning.currentText(),
            "reasoning_budget": self.reasoning_budget.value(),
        }

    def set_values(self, d: dict) -> None:
        for spin, key, default in [
            (self.n_predict, "n_predict", -1), (self.top_k, "top_k", 40),
            (self.repeat_last_n, "repeat_last_n", 64), (self.seed, "seed", -1),
            (self.reasoning_budget, "reasoning_budget", -1),
        ]:
            spin.blockSignals(True)
            spin.setValue(d.get(key) if d.get(key) is not None else default)
            spin.blockSignals(False)
        for spin, key, default in [
            (self.temp, "temperature", 0.8), (self.top_p, "top_p", 0.95),
            (self.min_p, "min_p", 0.05), (self.repeat_penalty, "repeat_penalty", 1.0),
            (self.presence, "presence_penalty", 0.0),
            (self.frequency, "frequency_penalty", 0.0),
        ]:
            spin.blockSignals(True)
            spin.setValue(d.get(key) if d.get(key) is not None else default)
            spin.blockSignals(False)
        self.reasoning.blockSignals(True)
        self.reasoning.setCurrentText(d.get("reasoning") or "auto")
        self.reasoning.blockSignals(False)
