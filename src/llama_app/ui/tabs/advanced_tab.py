"""Advanced tab: multi-GPU split, LoRA, HF download, log verbosity, etc."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

_SPLIT_MODES = ["layer", "none", "row", "tensor"]


class AdvancedTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.split_mode = QComboBox(); self.split_mode.addItems(_SPLIT_MODES); self.split_mode.setCurrentText("layer")
        self.tensor_split = QLineEdit(); self.tensor_split.setPlaceholderText("如 3,1 (逗号分隔)")
        self.main_gpu = QSpinBox(); self.main_gpu.setRange(0, 16); self.main_gpu.setValue(0)

        self.lora_list = QListWidget()
        add_lora_btn = QPushButton("添加…")
        remove_lora_btn = QPushButton("移除")
        add_lora_btn.clicked.connect(self._on_add_lora)
        remove_lora_btn.clicked.connect(self._on_remove_lora)
        lora_row = QHBoxLayout()
        lora_row.addWidget(self.lora_list, 1)
        lora_col = QVBoxLayout()
        lora_col.addWidget(add_lora_btn)
        lora_col.addWidget(remove_lora_btn)
        lora_col.addStretch(1)
        lora_row.addLayout(lora_col)

        self.hf_repo = QLineEdit(); self.hf_repo.setPlaceholderText("ggml-org/Qwen2.5-7B-Instruct-GGUF:Q4_K_M")
        self.hf_file = QLineEdit(); self.hf_file.setPlaceholderText("(可选)")
        self.hf_token = QLineEdit(); self.hf_token.setEchoMode(QLineEdit.Password)

        self.timeout = QSpinBox(); self.timeout.setRange(1, 86_400); self.timeout.setValue(3600)
        self.timeout.setSuffix(" s")
        self.verbose = QCheckBox("verbose (-v)")
        self.log_verbosity = QSpinBox(); self.log_verbosity.setRange(0, 5); self.log_verbosity.setValue(3)
        self.no_warmup = QCheckBox("跳过预热 (--no-warmup)")
        self.cache_prompt = QCheckBox("启用 prompt 缓存 (--cache-prompt)")
        self.cache_prompt.setChecked(True)

        for w in (self.split_mode,):
            w.currentTextChanged.connect(lambda _t: self.changed.emit())
        for w in (self.tensor_split, self.hf_repo, self.hf_file, self.hf_token):
            w.textChanged.connect(lambda _t: self.changed.emit())
        for w in (self.main_gpu, self.timeout, self.log_verbosity):
            w.valueChanged.connect(lambda _v: self.changed.emit())
        for w in (self.verbose, self.no_warmup, self.cache_prompt):
            w.toggled.connect(lambda _v: self.changed.emit())

        form = QFormLayout()
        form.addRow(self._section("以下仅在多 GPU 时使用"))
        form.addRow("split-mode (-sm):", self.split_mode)
        form.addRow("tensor-split (-ts):", self.tensor_split)
        form.addRow("main-gpu (-mg):", self.main_gpu)
        form.addRow(self._section("LoRA"))
        form.addRow(lora_row)
        form.addRow(self._section("HuggingFace 一键下载"))
        form.addRow("hf-repo (--hf-repo):", self.hf_repo)
        form.addRow("hf-file (--hf-file):", self.hf_file)
        form.addRow("hf-token:", self.hf_token)
        form.addRow(self._section("运行时"))
        form.addRow("timeout (-to):", self.timeout)
        form.addRow("log-verbosity (-lv):", self.log_verbosity)
        form.addRow(self.verbose)
        form.addRow(self.no_warmup)
        form.addRow(self.cache_prompt)

        outer = QVBoxLayout(self)
        outer.addLayout(form)
        outer.addStretch(1)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(f"<b>{text}</b>")
        lbl.setStyleSheet("color: palette(mid);")
        return lbl

    def _on_add_lora(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "选择 LoRA 适配器", "", "GGUF (*.gguf);;All files (*)")
        for p in paths:
            self.lora_list.addItem(p)
        if paths:
            self.changed.emit()

    def _on_remove_lora(self) -> None:
        for item in self.lora_list.selectedItems():
            self.lora_list.takeItem(self.lora_list.row(item))
        self.changed.emit()

    def values(self) -> dict:
        loras = [self.lora_list.item(i).text() for i in range(self.lora_list.count())]
        return {
            "split_mode": self.split_mode.currentText() if self.split_mode.currentText() != "layer" else None,
            "tensor_split": self.tensor_split.text() or None,
            "main_gpu": self.main_gpu.value() or None,
            "lora": loras,
            "hf_repo": self.hf_repo.text() or None,
            "hf_file": self.hf_file.text() or None,
            "hf_token": self.hf_token.text() or None,
            "timeout": self.timeout.value(),
            "verbose": self.verbose.isChecked(),
            "log_verbosity": self.log_verbosity.value(),
            "no_warmup": self.no_warmup.isChecked(),
            "cache_prompt": self.cache_prompt.isChecked(),
        }

    def set_values(self, d: dict) -> None:
        self.split_mode.blockSignals(True)
        self.split_mode.setCurrentText(d.get("split_mode") or "layer")
        self.split_mode.blockSignals(False)
        for w, key, default in [
            (self.tensor_split, "tensor_split", ""), (self.hf_repo, "hf_repo", ""),
            (self.hf_file, "hf_file", ""), (self.hf_token, "hf_token", ""),
        ]:
            w.blockSignals(True)
            w.setText(d.get(key) or default)
            w.blockSignals(False)
        for w, key, default in [
            (self.main_gpu, "main_gpu", 0), (self.timeout, "timeout", 3600),
            (self.log_verbosity, "log_verbosity", 3),
        ]:
            w.blockSignals(True)
            w.setValue(d.get(key) if d.get(key) is not None else default)
            w.blockSignals(False)
        for w, key, default in [
            (self.verbose, "verbose", False), (self.no_warmup, "no_warmup", False),
            (self.cache_prompt, "cache_prompt", True),
        ]:
            w.blockSignals(True)
            w.setChecked(bool(d.get(key, default)))
            w.blockSignals(False)
        self.lora_list.clear()
        for path in d.get("lora", []):
            self.lora_list.addItem(path)
