"""Application bootstrap."""
from __future__ import annotations

import sys

from . import APP_NAME, paths

STYLE = """
QMainWindow, QDialog, QWidget { font-size: 13px; }
QTabBar::tab { padding: 8px 18px; }
QFrame#card { background: #f4f6f9; border: 1px solid #d5dae2; border-radius: 8px; padding: 10px; }
QLabel#cardTitle { color: #556; font-size: 12px; }
QLabel#cardValue { font-size: 24px; font-weight: bold; }
QPushButton { padding: 6px 14px; }
QGroupBox { font-weight: bold; margin-top: 10px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }
"""


def run() -> int:
    from PySide6.QtWidgets import QApplication, QMessageBox

    from . import db
    from .service import KhataService
    from .ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE)

    try:
        service = KhataService(paths.db_path())
    except (db.DatabaseError, OSError) as exc:
        QMessageBox.critical(None, APP_NAME, f"The data file could not be opened:\n\n{exc}\n\n{paths.db_path()}")
        return 1

    window = MainWindow(service)
    window.show()
    code = app.exec()
    service.close()
    return code
