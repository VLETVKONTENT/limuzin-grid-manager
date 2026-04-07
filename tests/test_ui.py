from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from limuzin_grid_manager.core.models import SmallNumberingDirection, SmallNumberingMode
from limuzin_grid_manager.ui.main_window import MainWindow


def test_main_window_has_export_tab_and_live_summary() -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    window = MainWindow()

    try:
        window.update_stats()

        tab_names = [window.workspace_tabs.tabText(index) for index in range(window.workspace_tabs.count())]
        assert "Экспорт" in tab_names
        assert window.export_filename.text() == "aq_grid.kml"
        assert "Будет создан 1 общий KML-файл." in window.export_summary.toPlainText()
        assert window.export_scroll_area.widgetResizable() is True
        assert window.export_scroll_area.widget().minimumWidth() >= 560
        assert window.export_summary.minimumHeight() >= 180
        assert window.project_status.text() == "Новый проект"
        assert window.preset_combo.count() >= 1

        window.export_format.setCurrentIndex(1)
        window.update_stats()

        assert window.export_filename.text() == "aq_grid_tiles.zip"
        assert "Внутри архива:" in window.export_summary.toPlainText()

        window.apply_preset("numbering_linear_columns")
        window.update_stats()

        assert window.small_numbering_mode.currentData() == SmallNumberingMode.LINEAR.value
        assert window.small_numbering_direction.currentData() == SmallNumberingDirection.BY_COLUMNS.value
    finally:
        window.close()
