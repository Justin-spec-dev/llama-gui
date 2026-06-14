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

_SPLIT_MODES = ["(默认)", "layer", "none", "row", "tensor"]


class AdvancedTab(QWidget):
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.split_mode = QComboBox(); self.split_mode.addItems(_SPLIT_MODES); self.split_mode.setCurrentText("(默认)")
        self.split_mode.setToolTip("多 GPU 拆分模式 (-sm / --split-mode)\n\nnone=仅使用一个 GPU\nlayer=按层分配到多 GPU（默认，流水线）\nrow=按行拆分权重（并行化）\ntensor=按张量拆分（实验性）")
        self.tensor_split = QLineEdit(); self.tensor_split.setPlaceholderText("如 3,1 (逗号分隔，留空=默认)")
        self.tensor_split.setToolTip("GPU 负载比例 (-ts / --tensor-split)\n\n按比例将模型分配到各 GPU\n如 \"3,1\" 表示 GPU0 承担 3/4，GPU1 承担 1/4")
        self.main_gpu = QSpinBox(); self.main_gpu.setRange(0, 16); self.main_gpu.setValue(0); self.main_gpu.setSpecialValueText("(默认)")
        self.main_gpu.setToolTip("主 GPU 索引 (-mg / --main-gpu)\n\nsplit-mode=none 时使用的 GPU\n或 split-mode=row 时存放中间结果的 GPU")

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
        self.hf_repo.setToolTip("HuggingFace 仓库 (--hf-repo)\n\n自动从 HuggingFace 下载模型\n格式: 用户名/模型名[:量化类型]\n默认量化 Q4_K_M")
        self.hf_file = QLineEdit(); self.hf_file.setPlaceholderText("(可选)")
        self.hf_file.setToolTip("HuggingFace 指定文件 (--hf-file)\n\n指定仓库中的具体模型文件名\n留空则自动选择")
        self.hf_token = QLineEdit(); self.hf_token.setEchoMode(QLineEdit.Password)
        self.hf_token.setToolTip("HuggingFace 访问令牌 (--hf-token)\n\n用于下载需要授权的模型（如 Llama）\n未设置时使用 HF_TOKEN 环境变量")

        self.timeout = QSpinBox(); self.timeout.setRange(0, 86_400); self.timeout.setValue(0); self.timeout.setSpecialValueText("(默认 3600s)")
        self.timeout.setSuffix(" s")
        self.timeout.setToolTip("HTTP 超时 (-to / --timeout)\n\n服务器读写超时时间（秒）\n默认 3600（1小时）")
        self.verbose = QCheckBox("verbose (-v)")
        self.verbose.setToolTip("详细日志 (-v / --verbose)\n\n输出所有级别的日志信息\n用于调试时查看完整运行日志")
        self.log_verbosity = QSpinBox(); self.log_verbosity.setRange(0, 5); self.log_verbosity.setValue(0); self.log_verbosity.setSpecialValueText("(默认 3)")
        self.log_verbosity.setToolTip("日志级别 (-lv / --log-verbosity)\n\n0=通用输出, 1=错误, 2=警告, 3=信息(默认)\n4=跟踪, 5=调试")
        self.no_warmup = QCheckBox("跳过预热 (--no-warmup)")
        self.no_warmup.setToolTip("跳过预热 (--no-warmup)\n\n默认启动时会空跑一次预热模型\n勾选后跳过，可加快启动速度")
        self.cache_prompt = QCheckBox("禁用 prompt 缓存（llama 默认: 启用）")
        self.cache_prompt.setToolTip("禁用 Prompt 缓存 (--no-cache-prompt)\n\nllama-server 默认缓存 prompt 以加速重复请求\n勾选此框 = 关闭缓存，节省显存")

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
            "split_mode": self.split_mode.currentText() if self.split_mode.currentText() != "(默认)" else None,
            "tensor_split": self.tensor_split.text() or None,
            "main_gpu": self.main_gpu.value() if not self.main_gpu.specialValueText() or self.main_gpu.value() != 0 else None,
            "lora": loras,
            "hf_repo": self.hf_repo.text() or None,
            "hf_file": self.hf_file.text() or None,
            "hf_token": self.hf_token.text() or None,
            "timeout": self.timeout.value() if not self.timeout.specialValueText() or self.timeout.value() != 0 else None,
            "verbose": True if self.verbose.isChecked() else None,
            "log_verbosity": self.log_verbosity.value() if not self.log_verbosity.specialValueText() or self.log_verbosity.value() != 0 else None,
            "no_warmup": True if self.no_warmup.isChecked() else None,
            "cache_prompt": False if self.cache_prompt.isChecked() else None,
        }

    def set_values(self, d: dict) -> None:
        self.split_mode.blockSignals(True)
        self.split_mode.setCurrentText(d.get("split_mode") or "(默认)")
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
            v = d.get(key)
            if v is not None and v != 0:
                w.setValue(v)
                w.setSpecialValueText("")
            else:
                w.setValue(0)
                w.setSpecialValueText("(默认)")
            w.blockSignals(False)
        for w, key, is_disable in [
            (self.verbose, "verbose", False), (self.no_warmup, "no_warmup", False),
            (self.cache_prompt, "cache_prompt", True),
        ]:
            w.blockSignals(True)
            if is_disable:
                w.setChecked(d.get(key) is False)
            else:
                w.setChecked(bool(d.get(key)))
            w.blockSignals(False)
        self.lora_list.clear()
        for path in d.get("lora", []):
            self.lora_list.addItem(path)
