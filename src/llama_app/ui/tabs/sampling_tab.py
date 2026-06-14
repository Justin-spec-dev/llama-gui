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

_REASONING_OPTS = ["(默认 auto)", "auto", "on", "off"]


def _int_val(spin: QSpinBox) -> int | None:
    if spin.specialValueText() and spin.value() == 0:
        return None
    return spin.value()


def _float_val(spin: QDoubleSpinBox) -> float | None:
    if spin.specialValueText() and spin.value() == 0.0:
        return None
    return spin.value()


class SamplingTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        def make_int(rmax: int) -> QSpinBox:
            s = QSpinBox()
            s.setRange(0, rmax)
            s.setValue(0)
            s.setSpecialValueText("(默认)")
            s.valueChanged.connect(lambda v, sp=s: (self.changed.emit(), sp.setSpecialValueText("") if v != 0 else None))
            return s

        def make_float(rmax: float, step: float) -> QDoubleSpinBox:
            s = QDoubleSpinBox()
            s.setRange(0.0, rmax)
            s.setSingleStep(step)
            s.setValue(0.0)
            s.setSpecialValueText("(默认)")
            s.valueChanged.connect(lambda v, sp=s: (self.changed.emit(), sp.setSpecialValueText("") if v != 0.0 else None))
            return s

        self.n_predict = make_int(1_000_000); self.n_predict.setSpecialValueText("(默认 无限)"); self.n_predict.setValue(0)
        self.n_predict.setToolTip("最大生成 token 数 (-n / --n-predict)\n\nllama 默认: -1（无限制）")
        self.temp = make_float(5.0, 0.05); self.temp.setSpecialValueText("(默认 0.8)"); self.temp.setValue(0.0)
        self.temp.setToolTip("温度 (--temp)\n\n控制随机性，0=确定，1+=创意\nllama 默认: 0.8")
        self.top_k = make_int(200); self.top_k.setSpecialValueText("(默认 40)"); self.top_k.setValue(0)
        self.top_k.setToolTip("Top-K 采样 (--top-k)\n\n从概率最高的 K 个 token 中选\n0=禁用\nllama 默认: 40")
        self.top_p = make_float(1.0, 0.01); self.top_p.setSpecialValueText("(默认 0.95)"); self.top_p.setValue(0.0)
        self.top_p.setToolTip("Top-P 核采样 (--top-p)\n\n累积概率达到 P 时截断\n1.0=禁用\nllama 默认: 0.95")
        self.min_p = make_float(1.0, 0.01); self.min_p.setSpecialValueText("(默认 0.05)"); self.min_p.setValue(0.0)
        self.min_p.setToolTip("Min-P 采样 (--min-p)\n\ntoken 概率必须 ≥ 最高概率的 P 倍\n0.0=禁用\nllama 默认: 0.05")
        self.repeat_penalty = make_float(2.0, 0.05); self.repeat_penalty.setSpecialValueText("(默认 1.0)"); self.repeat_penalty.setValue(0.0)
        self.repeat_penalty.setToolTip("重复惩罚 (--repeat-penalty)\n\n1.0=不惩罚，>1.0=惩罚重复\nllama 默认: 1.0（不禁用）")
        self.repeat_last_n = make_int(2048); self.repeat_last_n.setSpecialValueText("(默认 64)"); self.repeat_last_n.setValue(0)
        self.repeat_last_n.setToolTip("重复惩罚窗口 (--repeat-last-n)\n\n0=禁用, -1=全部上下文\nllama 默认: 64")
        self.presence = make_float(2.0, 0.05); self.presence.setSpecialValueText("(默认 0.0)"); self.presence.setValue(0.0)
        self.presence.setToolTip("存在惩罚 (--presence-penalty)\n\n正值=减少重复，0.0=禁用\nllama 默认: 0.0")
        self.frequency = make_float(2.0, 0.05); self.frequency.setSpecialValueText("(默认 0.0)"); self.frequency.setValue(0.0)
        self.frequency.setToolTip("频率惩罚 (--frequency-penalty)\n\n正值=减少高频词，0.0=禁用\nllama 默认: 0.0")
        self.seed = make_int(2**31 - 1); self.seed.setSpecialValueText("(默认 随机)"); self.seed.setValue(0)
        self.seed.setToolTip("随机种子 (-s / --seed)\n\n-1=随机，固定值=可复现输出\nllama 默认: -1（随机）")
        self.reasoning = QComboBox(); self.reasoning.addItems(["(默认 auto)", "auto", "on", "off"]); self.reasoning.setCurrentText("(默认 auto)")
        self.reasoning.setToolTip("推理/思考模式 (--reasoning / -rea)\n\n控制 DeepSeek-R1、Qwen3 等思考模型的推理行为\non=强制输出思考过程, off=跳过思考, auto=从模板检测(默认)")
        self.reasoning.currentTextChanged.connect(lambda _t: self.changed.emit())
        self.reasoning_budget = make_int(1_000_000)
        self.reasoning_budget.setToolTip("推理 token 预算 (--reasoning-budget)\n\n限制思考过程使用的最大 token 数\n-1 = 无限制, 0 = 立即结束思考\n对支持思考的模型有效")

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
            "n_predict": _int_val(self.n_predict),
            "temperature": _float_val(self.temp),
            "top_k": _int_val(self.top_k),
            "top_p": _float_val(self.top_p),
            "min_p": _float_val(self.min_p),
            "repeat_penalty": _float_val(self.repeat_penalty),
            "repeat_last_n": _int_val(self.repeat_last_n),
            "presence_penalty": _float_val(self.presence),
            "frequency_penalty": _float_val(self.frequency),
            "seed": _int_val(self.seed),
            "reasoning": self.reasoning.currentText() if not self.reasoning.currentText().startswith("(默认") else None,
            "reasoning_budget": _int_val(self.reasoning_budget),
        }

    def set_values(self, d: dict) -> None:
        for spin, key, default in [
            (self.n_predict, "n_predict", -1), (self.top_k, "top_k", 40),
            (self.repeat_last_n, "repeat_last_n", 64), (self.seed, "seed", -1),
            (self.reasoning_budget, "reasoning_budget", -1),
        ]:
            spin.blockSignals(True)
            v = d.get(key)
            if v is not None:
                spin.setValue(v)
                spin.setSpecialValueText("")
            else:
                spin.setValue(0)
            spin.blockSignals(False)
        for spin, key, default in [
            (self.temp, "temperature", 0.8), (self.top_p, "top_p", 0.95),
            (self.min_p, "min_p", 0.05), (self.repeat_penalty, "repeat_penalty", 1.0),
            (self.presence, "presence_penalty", 0.0),
            (self.frequency, "frequency_penalty", 0.0),
        ]:
            spin.blockSignals(True)
            v = d.get(key)
            if v is not None:
                spin.setValue(v)
                spin.setSpecialValueText("")
            else:
                spin.setValue(0.0)
            spin.blockSignals(False)
        self.reasoning.blockSignals(True)
        self.reasoning.setCurrentText(d.get("reasoning") if d.get("reasoning") else "(默认 auto)")
        self.reasoning.blockSignals(False)
