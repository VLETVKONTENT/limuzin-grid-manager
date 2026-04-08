from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from limuzin_grid_manager.app.project import CoordinateState, ProjectState, save_project_state
from limuzin_grid_manager.core.models import GridOptions, SmallNumberingDirection, SmallNumberingMode
from limuzin_grid_manager.ui.main_window import LAST_PROJECT_PATH_KEY
from limuzin_grid_manager.ui.main_window import MainWindow


def test_main_window_has_export_tab_and_live_summary(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings, restore_last_project=False)

    try:
        window.update_stats()

        tab_names = [window.workspace_tabs.tabText(index) for index in range(window.workspace_tabs.count())]
        assert "Экспорт" in tab_names
        assert window.export_filename.text() == "aq_grid.kml"
        assert "Будет создан 1 общий KML-файл." in window.export_summary.toPlainText()
        assert window.export_format.count() >= 5
        assert window.export_scroll_area.widgetResizable() is True
        assert window.export_scroll_area.widget().minimumWidth() >= 560
        assert window.export_summary.minimumHeight() >= 180
        assert window.project_status.text() == "Новый проект"
        assert window.preset_combo.count() >= 1
        assert window.cancel_export_button.isHidden()
        assert window.export_cancel_button.isHidden()

        window.export_format.setCurrentIndex(1)
        window.update_stats()

        assert window.export_filename.text() == "aq_grid_tiles.zip"
        assert "Внутри архива:" in window.export_summary.toPlainText()
        assert "Оценка размера результата:" in window.export_summary.toPlainText()

        svg_index = window.export_format.findData("svg_schema")
        assert svg_index >= 0
        window.export_format.setCurrentIndex(svg_index)
        window.update_stats()

        assert window.export_filename.text() == "aq_grid.svg"
        assert "Будет создан 1 SVG-файл." in window.export_summary.toPlainText()
        assert "Объектов SVG к записи:" in window.export_summary.toPlainText()

        geojson_index = window.export_format.findData("geojson_gis")
        assert geojson_index >= 0
        window.export_format.setCurrentIndex(geojson_index)
        window.update_stats()

        assert window.export_filename.text() == "aq_grid.geojson"
        assert "Будет создан 1 GeoJSON-файл FeatureCollection." in window.export_summary.toPlainText()
        assert "Объектов GeoJSON к записи:" in window.export_summary.toPlainText()

        csv_index = window.export_format.findData("csv_table")
        assert csv_index >= 0
        window.export_format.setCurrentIndex(csv_index)
        window.update_stats()

        assert window.export_filename.text() == "aq_grid.csv"
        assert "Будет создан 1 CSV-файл" in window.export_summary.toPlainText()
        assert "Объектов CSV к записи:" in window.export_summary.toPlainText()

        window._set_export_running(True)
        assert not window.cancel_export_button.isHidden()
        assert window.cancel_export_button.isEnabled()
        assert not window.export_cancel_button.isHidden()
        assert window.export_cancel_button.isEnabled()
        window._set_export_running(False)

        window.apply_preset("numbering_linear_columns")
        window.update_stats()

        assert window.small_numbering_mode.currentData() == SmallNumberingMode.LINEAR.value
        assert window.small_numbering_direction.currentData() == SmallNumberingDirection.BY_COLUMNS.value
    finally:
        window.close()


def test_main_window_restores_last_project_from_settings(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    project_path = save_project_state(
        tmp_path / "saved-profile",
        ProjectState(
            coordinates=CoordinateState(
                x_nw="5661000",
                y_nw="6651000",
                x_se="5651000",
                y_se="6661000",
            ),
            options=GridOptions(),
            export_folder=str(tmp_path),
            export_filename="saved-profile.kml",
        ),
    )

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue(LAST_PROJECT_PATH_KEY, str(project_path))
    settings.sync()

    window = MainWindow(settings=settings)

    try:
        assert window.project_status.text() == f"Проект: {project_path.name}"
        assert window.project_status.toolTip() == str(project_path)
        assert window.x_nw.text() == "5661000"
        assert window.export_filename.text() == "saved-profile.kml"
    finally:
        window.close()
