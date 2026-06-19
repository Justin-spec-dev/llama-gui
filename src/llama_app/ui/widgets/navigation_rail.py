"""Persistent page navigation and compact resource summaries."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)


PAGES = (
    ("model", "模型 / 服务器", "选择模型与运行参数"),
    ("performance", "性能", "CPU / GPU 与并行设置"),
    ("network", "网络", "监听地址与端口"),
    ("sampling", "采样", "生成行为与随机性"),
    ("advanced", "高级设置", "低频与扩展选项"),
    ("monitor", "监控", "资源与运行状态"),
    ("presets", "预设配置", "保存与管理配置"),
)


def _number(value: float) -> str:
    return f"{value:g}"


class NavigationRail(QFrame):
    """Selects one of the stable workbench pages."""

    PAGES = PAGES
    page_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("navigationRail")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.page_list = QListWidget(self)
        self.page_list.setObjectName("navigationPages")
        self.page_list.setAccessibleName("工作区导航")
        self.page_list.setWordWrap(True)
        self.page_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for key, title, description in PAGES:
            item = QListWidgetItem(f"{title}\n{description}")
            item.setData(Qt.UserRole, key)
            item.setToolTip(description)
            self.page_list.addItem(item)
        self.page_list.currentItemChanged.connect(self._on_current_item_changed)
        layout.addWidget(self.page_list, 1)

        resources = QFrame(self)
        resources.setObjectName("resourceSummary")
        resource_layout = QVBoxLayout(resources)
        resource_layout.setContentsMargins(8, 8, 8, 8)
        self._resource_labels: dict[str, QLabel] = {}
        for key, label in (("cpu", "CPU"), ("ram", "RAM"), ("vram", "VRAM"), ("gpu", "GPU")):
            value = QLabel(f"{label}  N/A", resources)
            value.setObjectName("resourceValue")
            self._resource_labels[key] = value
            resource_layout.addWidget(value)
        layout.addWidget(resources)

        self.page_list.setCurrentRow(0)

    def _on_current_item_changed(self, current: QListWidgetItem | None) -> None:
        if current is not None:
            self.page_selected.emit(str(current.data(Qt.UserRole)))

    def select_page(self, key: str) -> None:
        for row in range(self.page_list.count()):
            item = self.page_list.item(row)
            if item.data(Qt.UserRole) == key:
                if self.page_list.currentRow() == row:
                    self.page_selected.emit(key)
                else:
                    self.page_list.setCurrentRow(row)
                return
        raise KeyError(key)

    def current_page(self) -> str:
        item = self.page_list.currentItem()
        return str(item.data(Qt.UserRole)) if item is not None else ""

    def resource_text(self, key: str) -> str:
        try:
            return self._resource_labels[key].text()
        except KeyError:
            raise KeyError(key) from None

    def update_resources(
        self,
        cpu: float,
        ram_gb: float,
        vram_gb: float | None,
        gpu: float | None,
    ) -> None:
        self._resource_labels["cpu"].setText(f"CPU  {_number(cpu)}%")
        self._resource_labels["ram"].setText(f"RAM  {_number(ram_gb)} GB")
        vram = "N/A" if vram_gb is None else f"{_number(vram_gb)} GB"
        gpu_text = "N/A" if gpu is None else f"{_number(gpu)}%"
        self._resource_labels["vram"].setText(f"VRAM  {vram}")
        self._resource_labels["gpu"].setText(f"GPU  {gpu_text}")

