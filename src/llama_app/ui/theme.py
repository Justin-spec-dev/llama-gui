"""Apply light/dark/auto theme to a QApplication."""
from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


_THEMES = ("light", "dark", "auto")


def _is_system_dark() -> bool:
    """Best-effort detection of system dark mode on Windows."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return value == 0
    except Exception:
        palette = QApplication.palette()
        bg = palette.color(QPalette.Window)
        return bg.lightness() < 128


def apply_theme(app: QApplication, theme: str) -> None:
    """Apply the named theme. Unknown values fall back to 'auto'."""
    if theme not in _THEMES:
        theme = "auto"
    if theme == "light":
        app.setStyleSheet("")
        return
    if theme == "dark":
        _apply_dark(app)
        return
    if _is_system_dark():
        _apply_dark(app)
    else:
        app.setStyleSheet("")


def _apply_dark(app: QApplication) -> None:
    try:
        import qdarkstyle
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=qdarkstyle.DarkPalette))
    except Exception:
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.Window, QPalette.color(QPalette.Window).darker(150))
        app.setPalette(palette)


def current_theme() -> str:
    return QSettings().value("ui/theme", "auto", type=str)


def save_theme(theme: str) -> None:
    QSettings().setValue("ui/theme", theme)
