from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from limuzin_grid_manager.app.runtime import configure_runtime_logging, install_exception_hooks
from limuzin_grid_manager.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("LIMUZIN GRID MANAGER")
    app.setOrganizationName("limuzin")
    configure_runtime_logging()
    install_exception_hooks()

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
