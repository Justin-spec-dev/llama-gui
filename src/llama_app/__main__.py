"""Entry point: ``python -m llama_app`` or the ``llama-gui`` script."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from llama_app.ui.main_window import MainWindow
from llama_app.ui.theme import apply_theme, current_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("llama-gui")
    app.setOrganizationName("llama-gui")
    apply_theme(app, current_theme())
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
