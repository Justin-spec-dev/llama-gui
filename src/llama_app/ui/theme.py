"""Apply light/dark/auto theme to a QApplication."""
from __future__ import annotations

import re
import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

_THEMES = ("light", "dark", "auto")


def _resources_dir() -> Path:
    """Return the directory holding icon assets.

    Works both in development (project tree) and when bundled by PyInstaller
    (onefile mode unpacks to ``sys._MEIPASS``).
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidate = Path(meipass) / "llama_app" / "resources"
        if candidate.is_dir():
            return candidate
    return Path(__file__).resolve().parent.parent / "resources"


def _arrow_url(name: str) -> str:
    """Return a QSS ``url(...)`` for a spinbox arrow asset, or empty string."""
    path = _resources_dir() / name
    if path.is_file():
        # Forward slashes + absolute path is the most portable form for Qt's
        # stylesheet URL parser on Windows.
        return path.as_posix()
    return ""


def _spinbox_arrows_qss(theme: str) -> str:
    """Build the QSpinBox arrow rules pointing at on-disk PNG assets.

    QSS ``image: url(...)`` only loads from real paths or registered Qt
    resources — not ``data:`` URIs — so the PNGs are stored alongside
    ``icon.png`` and bundled by PyInstaller. When the assets are missing
    (e.g. the package was renamed or icons were deleted), the rules collapse
    to ``image: none`` rather than rendering broken glyphs.
    """
    if theme == "dark":
        up_url = _arrow_url("spin_up_dark.png")
        down_url = _arrow_url("spin_down_dark.png")
    else:
        up_url = _arrow_url("spin_up_light.png")
        down_url = _arrow_url("spin_down_light.png")
    up_image = f"image: url({up_url});" if up_url else "image: none;"
    down_image = f"image: url({down_url});" if down_url else "image: none;"
    return (
        f"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow "
        f"{{ width: 12px; height: 7px; {up_image} }}\n"
        f"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow "
        f"{{ width: 12px; height: 7px; {down_image} }}\n"
    )

# Shared structural styles — font sizes, spacing, padding NEVER change
_BASE_QSS = """
QWidget {
    font-family: "Microsoft YaHei UI", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 11.5pt;
}
QPushButton:focus, QComboBox:focus, QListWidget:focus, QCheckBox:focus { border: 1px solid $accent; }

QTabWidget::pane { border: 1px solid $border; border-radius: 4px; margin-top: -1px; }
QTabBar::tab { padding: 7px 18px; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px; min-width: 72px; }
QTabBar::tab:selected { font-weight: bold; }

QPushButton { border: 1px solid $border; border-radius: 4px; padding: 5px 14px; min-height: 32px; font-size: 12pt; }
QPushButton:hover { border-color: $accent; }
QPushButton:pressed { background: $press; }
QPushButton:disabled { color: $mutedText; }

/* Primary button — solid accent surface, white text */
QPushButton[role="primary"] {
    background: $accent;
    color: $selectedText;
    border: 1px solid $accent;
    border-radius: 4px;
    padding: 5px 18px;
    min-height: 32px;
    font-size: 12pt;
    font-weight: 600;
}
QPushButton[role="primary"]:hover  { background: $accentPressed; border-color: $accentPressed; }
QPushButton[role="primary"]:pressed { background: $accentPressed; border-color: $accentPressed; padding-top: 6px; padding-bottom: 4px; }
QPushButton[role="primary"]:disabled { background: $mutedSurface; color: $mutedText; border-color: $border; font-weight: 500; }

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { border: 1px solid $border; border-radius: 4px; padding: 3px 8px; min-height: 30px; font-size: 11.5pt; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: $accent; }
QComboBox QAbstractItemView { border: 1px solid $border; selection-background-color: $accent; }
QComboBox::drop-down { border: none; padding-right: 4px; }
QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border; subcontrol-position: top right; width: 18px; height: 14px; border-left: 1px solid $border; border-bottom: 1px solid $border; }
QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border; subcontrol-position: bottom right; width: 18px; height: 14px; border-left: 1px solid $border; }
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background: $hoverSurface; }
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed { background: $press; }
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { width: 12px; height: 7px; }
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { width: 12px; height: 7px; }

QCheckBox { spacing: 7px; font-size: 11.5pt; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid $border; border-radius: 3px; }

QGroupBox { border: 1px solid $border; border-radius: 5px; margin-top: 14px; padding-top: 16px; font-size: 12pt; font-weight: 600; }
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
QListWidget#navigationPages::item { border-radius: 8px; padding: 12px 12px 12px 14px; margin: 4px 6px; font-size: 11.5pt; font-weight: 500; border-left: 3px solid transparent; }
QListWidget#navigationPages::item:selected { background: $navSelected; color: $navSelectedText; border-left: 3px solid $accent; font-weight: 600; }
QListWidget#navigationPages::item:hover:!selected { background: $hoverSurface; }
QFrame#resourceSummary { border: 1px solid $border; border-radius: 5px; }
QLabel#resourceValue { background: transparent; font-size: 11pt; font-weight: 500; }

QFrame#commandBar { border: 1px solid $border; border-radius: 5px; }
QFrame#commandBar QLabel { background: transparent; font-size: 11.5pt; }
QLabel#modelSummary { color: $mutedText; font-size: 11pt; }
QLabel#dirtyState { color: $warningText; font-weight: bold; }
QLabel#serverState { border-radius: 11px; padding: 4px 12px 4px 26px; font-size: 12pt; font-weight: 600; border: 1px solid transparent; }
QLabel#serverState[state="ready"] { color: $successText; background: $successSurface; border-color: $successSurface; }
QLabel#serverState[state="error"] { color: $errorText; background: $errorSurface; border-color: $errorSurface; }
QLabel#serverState[state="starting"], QLabel#serverState[state="loading"] { color: $warningText; background: $warningSurface; border-color: $warningSurface; }
QLabel#serverState[state="stopped"] { color: $mutedText; background: $mutedSurface; border-color: $mutedSurface; }
QLabel#sectionTitle { padding: 14px 0 8px 0; font-size: 14pt; font-weight: 600; color: $accent; border-top: 1px solid $border; margin-top: 6px; }
QMenuBar, QMenu, QStatusBar { font-size: 11pt; }
"""

_DARK_VARS = {
    "$border": "#334155",
    "$accent": "#60a5fa",
    "$accentPressed": "#3b82f6",
    "$accentSoft": "#1e3a8a",
    "$accentOnSoft": "#bfdbfe",
    "$press": "#1e293b",
    "$selectedText": "#ffffff",
    "$navSelected": "#1e3a8a",
    "$navSelectedText": "#bfdbfe",
    "$hoverSurface": "#1f2937",
    "$mutedText": "#94a3b8",
    "$warningText": "#fbbf24",
    "$successText": "#86efac",
    "$successSurface": "#14532d",
    "$errorText": "#fca5a5",
    "$errorSurface": "#7f1d1d",
    "$warningSurface": "#78350f",
    "$mutedSurface": "#1e293b",
    "$plot1": "#60a5fa",
    "$plot2": "#38bdf8",
    "$plot3": "#fbbf24",
    "$plot4": "#34d399",
}

_DARK_QSS = _BASE_QSS + """
QWidget { color: #c8c8d0; background-color: #1c1c28; }
QTabWidget::pane { background: #181824; }
QTabBar::tab { background: #222233; color: #889; }
QTabBar::tab:selected { background: #1c2c3c; color: $accent; }
QTabBar::tab:hover:!selected { background: #2a2a3c; }
QPushButton { background: #2a2a3c; color: #c8c8d0; }
QPushButton:hover { background: #343450; }
QPushButton:disabled { background: #1a1a26; color: #556; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #222233; color: #c8c8d0; }
QComboBox QAbstractItemView { background: #222233; color: #c8c8d0; }
QCheckBox { color: #b0b0c0; }
QCheckBox::indicator { background: #222233; }
QCheckBox::indicator:checked { background: $accent; }
QGroupBox { color: $accent; }
QGroupBox::title { background: #1c1c28; }
QToolBar { background: #181824; }
QScrollBar:vertical { background: #1c1c28; }
QScrollBar::handle:vertical { background: $border; }
QTextEdit { background: #14141e; color: #b0b0c0; }
QStatusBar { background: #141421; color: #889; }
QMenuBar { background: #181824; color: #b0b0c0; }
QMenuBar::item:selected { background: #2a2a3c; }
QMenuBar::item { padding: 4px 10px; }
QMenu { background: #222233; color: #c8c8d0; }
QMenu::item { padding: 5px 28px; }
QMenu::item:selected { background: $accent; color: $selectedText; }
QListWidget { background: #222233; color: #c8c8d0; }
QListWidget::item:hover { background: $hoverSurface; }
QFormLayout QLabel { color: #8899aa; }
"""

_LIGHT_VARS = {
    "$border": "#cbd5e1",
    "$accent": "#2563eb",
    "$accentPressed": "#1d4ed8",
    "$accentSoft": "#dbeafe",
    "$accentOnSoft": "#1e3a8a",
    "$press": "#d6dbe3",
    "$selectedText": "#ffffff",
    "$navSelected": "#dbeafe",
    "$navSelectedText": "#1e3a8a",
    "$hoverSurface": "#eef2f7",
    "$mutedText": "#475569",
    "$warningText": "#b45309",
    "$successText": "#15803d",
    "$successSurface": "#dcfce7",
    "$errorText": "#b91c1c",
    "$errorSurface": "#fee2e2",
    "$warningSurface": "#fef3c7",
    "$mutedSurface": "#e5e7eb",
    "$plot1": "#2563eb",
    "$plot2": "#0ea5e9",
    "$plot3": "#f59e0b",
    "$plot4": "#10b981",
}

_LIGHT_QSS = _BASE_QSS + """
QWidget { color: #333; background-color: #f5f5f5; }
QTabWidget::pane { background: #ffffff; }
QTabBar::tab { background: #e8e8ec; color: #667; }
QTabBar::tab:selected { background: #dce8f0; color: $accent; }
QTabBar::tab:hover:!selected { background: #eef0f4; }
QPushButton { background: #e0e0e4; color: #333; }
QPushButton:hover { background: #d4d4dc; }
QPushButton:disabled { background: #f0f0f0; color: #aaa; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; color: #333; }
QComboBox QAbstractItemView { background: #ffffff; color: #333; }
QCheckBox { color: #444; }
QCheckBox::indicator { background: #ffffff; }
QCheckBox::indicator:checked { background: $accent; }
QGroupBox { color: $accent; }
QGroupBox::title { background: #f5f5f5; }
QToolBar { background: #eeeeee; }
QScrollBar:vertical { background: #f5f5f5; }
QScrollBar::handle:vertical { background: $border; }
QTextEdit { background: #fafafa; color: #333; }
QStatusBar { background: #eee; color: #888; }
QMenuBar { background: #eeeeee; color: #444; }
QMenuBar::item:selected { background: #dce8f0; }
QMenuBar::item { padding: 4px 10px; }
QMenu { background: #ffffff; color: #333; }
QMenu::item { padding: 5px 28px; }
QMenu::item:selected { background: $accent; color: $selectedText; }
QListWidget { background: #ffffff; color: #333; }
QListWidget::item:hover { background: $hoverSurface; }
QFormLayout QLabel { color: $mutedText; }
"""


def _subst(qss: str, vars: dict) -> str:
    # Token-aware replace: substitute "$name" only as a whole word so prefixes
    # like "$accent" don't greedily match "$accentPressed".
    pattern = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")
    return pattern.sub(lambda m: vars.get(f"${m.group(1)}", m.group(0)), qss)


def _is_system_dark() -> bool:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        return False


def _sync_pyqtgraph_theme(theme: str) -> None:
    """Keep pyqtgraph's axis/foreground colors in sync with the active theme."""
    try:
        import pyqtgraph as pg
    except ImportError:
        return
    if theme == "dark":
        pg.setConfigOption("foreground", "#cbd5e1")
        pg.setConfigOption("background", "#1c1c28")
    else:
        pg.setConfigOption("foreground", "#334155")
        pg.setConfigOption("background", "#f5f5f5")


def apply_theme(app: QApplication, theme: str) -> None:
    if theme not in _THEMES:
        theme = "auto"
    if theme == "auto":
        theme = "dark" if _is_system_dark() else "light"

    base = _DARK_QSS if theme == "dark" else _LIGHT_QSS
    vars_ = _DARK_VARS if theme == "dark" else _LIGHT_VARS
    app.setStyleSheet(_subst(base, vars_) + _spinbox_arrows_qss(theme))
    _sync_pyqtgraph_theme(theme)


def current_theme() -> str:
    return QSettings().value("ui/theme", "auto", type=str)


def save_theme(theme: str) -> None:
    QSettings().setValue("ui/theme", theme)