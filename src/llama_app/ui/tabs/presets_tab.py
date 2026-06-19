"""Presets tab: list of saved presets with save/load/rename/delete buttons."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from llama_app.core.config import Config
from llama_app.core.presets import Preset, PresetStore


class PresetsTab(QWidget):
    preset_loaded = Signal(Config)
    save_requested = Signal()

    def __init__(self, store: PresetStore | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._store = store or PresetStore()

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_load_clicked)

        self._summary = QLabel("(未选择)")
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet("color: palette(mid);")

        self._load_btn = QPushButton("加载")
        self._save_btn = QPushButton("保存当前为预设…")
        self._rename_btn = QPushButton("重命名…")
        self._delete_btn = QPushButton("删除")
        for button, name in (
            (self._load_btn, "加载选中的预设"),
            (self._save_btn, "保存当前配置为预设"),
            (self._rename_btn, "重命名选中的预设"),
            (self._delete_btn, "删除选中的预设"),
        ):
            button.setAccessibleName(name)

        self._load_btn.clicked.connect(self._on_load_clicked)
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._rename_btn.clicked.connect(self._on_rename_clicked)
        self._delete_btn.clicked.connect(self._on_delete_clicked)
        self.list_widget.currentItemChanged.connect(self._on_selection_changed)

        buttons = QHBoxLayout()
        buttons.addWidget(self._load_btn)
        buttons.addWidget(self._save_btn)
        buttons.addStretch(1)
        buttons.addWidget(self._rename_btn)
        buttons.addWidget(self._delete_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget, 1)
        layout.addWidget(self._summary)
        layout.addLayout(buttons)

        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        for p in self._store.list():
            self.list_widget.addItem(p.name)
        self._update_buttons()

    def selected_name(self) -> str | None:
        item = self.list_widget.currentItem()
        return item.text() if item else None

    def _update_buttons(self) -> None:
        has_sel = self.selected_name() is not None
        self._load_btn.setEnabled(has_sel)
        self._rename_btn.setEnabled(has_sel)
        self._delete_btn.setEnabled(has_sel)

    def _on_selection_changed(self, _current, _previous) -> None:
        name = self.selected_name()
        if not name:
            self._summary.setText("(未选择)")
        else:
            try:
                p = self._store.get(name)
                c = p.config
                bits = [
                    f"server: {c.server_path}",
                    f"model: {c.model_path}",
                    f"ngl: {c.n_gpu_layers}, ctx: {c.ctx_size}, threads: {c.threads}",
                ]
                self._summary.setText("\n".join(bits))
            except KeyError:
                self._summary.setText("(未找到)")
        self._update_buttons()

    def _on_load_clicked(self) -> None:
        name = self.selected_name()
        if not name:
            return
        try:
            p = self._store.get(name)
        except KeyError:
            QMessageBox.warning(self, "错误", f"预设 '{name}' 不存在")
            return
        self.preset_loaded.emit(p.config)

    def _on_save_clicked(self) -> None:
        self.save_requested.emit()

    def _on_rename_clicked(self) -> None:
        old = self.selected_name()
        if not old:
            return
        new, ok = QInputDialog.getText(self, "重命名预设", "新名称:", text=old)
        if not ok or not new.strip():
            return
        new = new.strip()
        if new == old:
            return
        try:
            self._store.rename(old, new)
        except (KeyError, ValueError) as e:
            QMessageBox.warning(self, "重命名失败", str(e))
            return
        self.refresh()

    def _on_delete_clicked(self) -> None:
        name = self.selected_name()
        if not name:
            return
        confirm = QMessageBox.question(self, "确认删除", f"删除预设 '{name}'？")
        if confirm != QMessageBox.Yes:
            return
        try:
            self._store.delete(name)
        except KeyError as e:
            QMessageBox.warning(self, "删除失败", str(e))
            return
        self.refresh()

    def save_preset(self, name: str, config: Config) -> None:
        self._store.save(Preset.now(name=name, config=config))
        self.refresh()
        items = self.list_widget.findItems(name, Qt.MatchExactly)
        if items:
            self.list_widget.setCurrentItem(items[0])
