"""Reusable primitives for scrollable configuration pages."""
from __future__ import annotations

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSpinBox,
    QWidget,
)


def make_scroll_page(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setWidget(widget)
    return scroll


class SectionTitle(QLabel):
    def __init__(
        self, title: str, description: str = "", parent: QWidget | None = None
    ) -> None:
        text = f"<b>{title}</b>"
        if description:
            text += f"<br><span>{description}</span>"
        super().__init__(text, parent)
        self.setObjectName("sectionTitle")


class DefaultIntField(QWidget):
    changed = Signal()

    def __init__(
        self,
        minimum: int,
        maximum: int,
        default_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.spin = QSpinBox(self)
        self.spin.setRange(minimum, maximum)
        self.use_default = QCheckBox(
            f"使用 llama 默认值（{default_label}）", self
        )
        self.use_default.setChecked(True)
        self.spin.setEnabled(False)
        self.use_default.toggled.connect(self._default_toggled)
        self.spin.valueChanged.connect(self.changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin, 1)
        layout.addWidget(self.use_default)

    def _default_toggled(self, checked: bool) -> None:
        self.spin.setEnabled(not checked)
        self.changed.emit()

    def config_value(self) -> int | None:
        return None if self.use_default.isChecked() else self.spin.value()

    def set_config_value(self, value: int | None) -> None:
        old_value = self.config_value()
        spin_blocker = QSignalBlocker(self.spin)
        check_blocker = QSignalBlocker(self.use_default)
        if value is not None:
            self.spin.setValue(value)
        self.use_default.setChecked(value is None)
        self.spin.setEnabled(value is not None)
        del spin_blocker, check_blocker
        if self.config_value() != old_value:
            self.changed.emit()


class DefaultFloatField(QWidget):
    changed = Signal()

    def __init__(
        self,
        minimum: float,
        maximum: float,
        step: float,
        default_label: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.spin = QDoubleSpinBox(self)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step)
        self.use_default = QCheckBox(
            f"使用 llama 默认值（{default_label}）", self
        )
        self.use_default.setChecked(True)
        self.spin.setEnabled(False)
        self.use_default.toggled.connect(self._default_toggled)
        self.spin.valueChanged.connect(self.changed)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.spin, 1)
        layout.addWidget(self.use_default)

    def _default_toggled(self, checked: bool) -> None:
        self.spin.setEnabled(not checked)
        self.changed.emit()

    def config_value(self) -> float | None:
        return None if self.use_default.isChecked() else self.spin.value()

    def set_config_value(self, value: float | None) -> None:
        old_value = self.config_value()
        spin_blocker = QSignalBlocker(self.spin)
        check_blocker = QSignalBlocker(self.use_default)
        if value is not None:
            self.spin.setValue(value)
        self.use_default.setChecked(value is None)
        self.spin.setEnabled(value is not None)
        del spin_blocker, check_blocker
        if self.config_value() != old_value:
            self.changed.emit()
