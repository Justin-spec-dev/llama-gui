"""Apply light/dark/auto theme to a QApplication."""
from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

_THEMES = ("light", "dark", "auto")

# Shared structural styles — font sizes, spacing, padding NEVER change
_BASE_QSS = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 11.5pt;
}
QPushButton:focus, QComboBox:focus, QListWidget:focus, QCheckBox:focus { border: 1px solid $accent; }

QTabWidget::pane { border: 1px solid $border; border-radius: 4px; margin-top: -1px; }
QTabBar::tab { padding: 6px 16px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; min-width: 64px; }
QTabBar::tab:selected { font-weight: bold; }

QPushButton { border: 1px solid $border; border-radius: 4px; padding: 5px 14px; min-height: 30px; font-size: 12pt; }
QPushButton:hover { border-color: $accent; }
QPushButton:pressed { background: $press; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { border: 1px solid $border; border-radius: 4px; padding: 3px 8px; min-height: 28px; font-size: 11.5pt; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: $accent; }
QComboBox QAbstractItemView { border: 1px solid $border; selection-background-color: $accent; }
QComboBox::drop-down { border: none; padding-right: 4px; }
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button { width: 16px; border-left: 1px solid $border; }

QCheckBox { spacing: 7px; font-size: 11.5pt; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid $border; border-radius: 3px; }

QGroupBox { border: 1px solid $border; border-radius: 5px; margin-top: 12px; padding-top: 14px; font-size: 12pt; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }

QToolBar { border-bottom: 1px solid $border; spacing: 4px; padding: 3px 6px; }
QToolBar QPushButton { font-weight: bold; padding: 4px 14px; min-width: 50px; }

QSplitter::handle { height: 2px; }
QScrollBar:vertical { width: 8px; border-radius: 4px; }
QScrollBar::handle:vertical { border-radius: 4px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QTextEdit { border: 1px solid $border; border-radius: 3px; padding: 3px; }

QListWidget { border: 1px solid $border; border-radius: 3px; padding: 2px; }
QListWidget::item { padding: 4px 6px; }
QListWidget::item:selected { background: $accent; color: $selectedText; }

QFrame#navigationRail { border-right: 1px solid $border; }
QListWidget#navigationPages { border: none; background: transparent; padding: 0; }
QListWidget#navigationPages::item { border-radius: 6px; padding: 12px 10px; margin: 3px 0; font-size: 11.5pt; font-weight: 500; }
QListWidget#navigationPages::item:selected { background: $navSelected; color: $navSelectedText; border-left: 3px solid $accent; }
QListWidget#navigationPages::item:hover:!selected { background: $hoverSurface; }
QFrame#resourceSummary { border: 1px solid $border; border-radius: 5px; }
QLabel#resourceValue { background: transparent; font-size: 11pt; font-weight: 500; }

QFrame#commandBar { border: 1px solid $border; border-radius: 5px; }
QFrame#commandBar QLabel { background: transparent; font-size: 11.5pt; }
QLabel#modelSummary { color: $mutedText; font-size: 11pt; }
QLabel#dirtyState { color: $warningText; font-weight: bold; }
QLabel#serverState { border-radius: 11px; padding: 4px 11px; font-size: 12pt; font-weight: 600; }
QLabel#serverState[state="ready"] { color: $successText; background: $successSurface; }
QLabel#serverState[state="error"] { color: $errorText; background: $errorSurface; }
QLabel#serverState[state="starting"], QLabel#serverState[state="loading"] { color: $warningText; background: $warningSurface; }
QLabel#serverState[state="stopped"] { color: $mutedText; background: $mutedSurface; }
QLabel#sectionTitle { padding: 6px 0; font-size: 14pt; font-weight: 600; }
QMenuBar, QMenu, QStatusBar { font-size: 11pt; }
"""

_DARK_VARS = {
    "$border": "#3a3a50",
    "$accent": "#4a8abc",
    "$press": "#2a3a4a",
    "$selectedText": "#ffffff",
    "$navSelected": "#1c3850",
    "$navSelectedText": "#8dcaf0",
    "$hoverSurface": "#2a2a3c",
    "$mutedText": "#9292a2",
    "$warningText": "#f0b45d",
    "$successText": "#76d28a",
    "$successSurface": "#203c2a",
    "$errorText": "#ff8a8a",
    "$errorSurface": "#482626",
    "$warningSurface": "#45371f",
    "$mutedSurface": "#292936",
}

_DARK_QSS = _BASE_QSS + """
QWidget { color: #c8c8d0; background-color: #1c1c28; }
QTabWidget::pane { background: #181824; }
QTabBar::tab { background: #222233; color: #889; }
QTabBar::tab:selected { background: #1c2c3c; color: #6ab0d0; }
QTabBar::tab:hover:!selected { background: #2a2a3c; }
QPushButton { background: #2a2a3c; color: #c8c8d0; }
QPushButton:hover { background: #343450; }
QPushButton:disabled { background: #1a1a26; color: #556; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #222233; color: #c8c8d0; }
QComboBox QAbstractItemView { background: #222233; color: #c8c8d0; }
QCheckBox { color: #b0b0c0; }
QCheckBox::indicator { background: #222233; }
QCheckBox::indicator:checked { background: #4a8abc; }
QGroupBox { color: #6ab0d0; }
QGroupBox::title { background: #1c1c28; }
QToolBar { background: #181824; }
QScrollBar:vertical { background: #1c1c28; }
QScrollBar::handle:vertical { background: #3a3a50; }
QTextEdit { background: #14141e; color: #b0b0c0; }
QStatusBar { background: #141421; color: #889; }
QMenuBar { background: #181824; color: #b0b0c0; }
QMenuBar::item:selected { background: #2a2a3c; }
QMenuBar::item { padding: 4px 10px; }
QMenu { background: #222233; color: #c8c8d0; }
QMenu::item { padding: 5px 28px; }
QMenu::item:selected { background: $accent; color: $selectedText; }
QMenu { background: #222233; color: #c8c8d0; }
QListWidget { background: #222233; color: #c8c8d0; }
QListWidget::item:hover { background: #2a3a4c; }
QFormLayout QLabel { color: #8899aa; }
"""

_LIGHT_VARS = {
    "$border": "#c0c0cc",
    "$accent": "#3a7abf",
    "$press": "#d0d8e0",
    "$selectedText": "#ffffff",
    "$navSelected": "#dceaf8",
    "$navSelectedText": "#165f9e",
    "$hoverSurface": "#e8eef5",
    "$mutedText": "#667788",
    "$warningText": "#8a5b00",
    "$successText": "#237a3b",
    "$successSurface": "#dff3e4",
    "$errorText": "#a52b2b",
    "$errorSurface": "#f8dfdf",
    "$warningSurface": "#f7ecd1",
    "$mutedSurface": "#e7e9ed",
}

_LIGHT_QSS = _BASE_QSS + """
QWidget { color: #333; background-color: #f5f5f5; }
QTabWidget::pane { background: #ffffff; }
QTabBar::tab { background: #e8e8ec; color: #667; }
QTabBar::tab:selected { background: #dce8f0; color: #2068a0; }
QTabBar::tab:hover:!selected { background: #eef0f4; }
QPushButton { background: #e0e0e4; color: #333; }
QPushButton:hover { background: #d4d4dc; }
QPushButton:disabled { background: #f0f0f0; color: #aaa; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; color: #333; }
QComboBox QAbstractItemView { background: #ffffff; color: #333; }
QCheckBox { color: #444; }
QCheckBox::indicator { background: #ffffff; }
QCheckBox::indicator:checked { background: #3a7abf; }
QGroupBox { color: #2068a0; }
QGroupBox::title { background: #f5f5f5; }
QToolBar { background: #eeeeee; }
QScrollBar:vertical { background: #f5f5f5; }
QScrollBar::handle:vertical { background: #c0c0cc; }
QTextEdit { background: #fafafa; color: #333; }
QStatusBar { background: #eee; color: #888; }
QMenuBar { background: #eeeeee; color: #444; }
QMenuBar::item:selected { background: #dce8f0; }
QMenuBar::item { padding: 4px 10px; }
QMenu { background: #ffffff; color: #333; }
QMenu::item { padding: 5px 28px; }
QMenu::item:selected { background: $accent; color: $selectedText; }
QMenu { background: #ffffff; color: #333; }
QListWidget { background: #ffffff; color: #333; }
QListWidget::item:hover { background: #dce8f0; }
QFormLayout QLabel { color: #667788; }
"""


def _subst(qss: str, vars: dict) -> str:
    for k, v in vars.items():
        qss = qss.replace(k, v)
    return qss


def _is_system_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def apply_theme(app: QApplication, theme: str) -> None:
    if theme not in _THEMES:
        theme = "auto"
    if theme == "auto":
        theme = "dark" if _is_system_dark() else "light"

    app.setStyleSheet(_subst(_DARK_QSS, _DARK_VARS) if theme == "dark" else _subst(_LIGHT_QSS, _LIGHT_VARS))


def current_theme() -> str:
    return QSettings().value("ui/theme", "auto", type=str)


def save_theme(theme: str) -> None:
    QSettings().setValue("ui/theme", theme)
