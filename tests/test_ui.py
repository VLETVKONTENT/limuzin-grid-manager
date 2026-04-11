from __future__ import annotations

import json
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QMessageBox
from PySide6.QtWidgets import QApplication
from openpyxl import Workbook

from limuzin_grid_manager.app import runtime as runtime_module
from limuzin_grid_manager.app.project import CoordinateState, ProjectState, project_state_to_dict, save_project_state
from limuzin_grid_manager.core.models import GridOptions, SmallNumberingDirection, SmallNumberingMode
from limuzin_grid_manager.core.points import PointStyle
from limuzin_grid_manager.ui.main_window import LAST_PROJECT_PATH_KEY, THEME_SETTINGS_KEY
from limuzin_grid_manager.ui.main_window import MainWindow
from limuzin_grid_manager.ui import points_window as points_window_module
from limuzin_grid_manager.ui.points_window import LAST_EXCEL_PATH_KEY, POINT_COLOR_KEY, POINT_OPACITY_KEY
from limuzin_grid_manager.ui.points_window import PointsWindow
from limuzin_grid_manager.ui.themes import DARK_THEME_ID, HIGH_CONTRAST_THEME_ID, SYSTEM_LIGHT_THEME_ID


def _write_points_workbook(path, rows) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Лист1"
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    workbook.close()

def _wait_until(predicate, timeout: float = 3.0) -> None:
    app = QApplication.instance() or QApplication([])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        time.sleep(0.01)
    app.processEvents()
    assert predicate()


def _wait_for_import(window: PointsWindow, timeout: float = 3.0) -> None:
    _wait_until(lambda: window._import_thread is None, timeout=timeout)


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
        assert window.theme_combo.currentData() == SYSTEM_LIGHT_THEME_ID
        assert window.export_scroll_area.widgetResizable() is True
        assert window.export_scroll_area.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        assert window.export_scroll_area.widget().minimumWidth() == 0
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


def test_theme_is_restored_from_settings_and_not_saved_to_project(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    settings.setValue(THEME_SETTINGS_KEY, DARK_THEME_ID)
    settings.sync()

    window = MainWindow(settings=settings, restore_last_project=False)

    try:
        assert window.theme_combo.currentData() == DARK_THEME_ID
        assert settings.value(THEME_SETTINGS_KEY, "", str) == DARK_THEME_ID

        window.apply_theme(HIGH_CONTRAST_THEME_ID)

        assert window.theme_combo.currentData() == HIGH_CONTRAST_THEME_ID
        assert settings.value(THEME_SETTINGS_KEY, "", str) == HIGH_CONTRAST_THEME_ID
        assert "font-size: 10.5pt" in app.styleSheet()

        data = project_state_to_dict(window._current_project_state())
        serialized = json.dumps(data, ensure_ascii=False)

        assert THEME_SETTINGS_KEY not in serialized
        assert HIGH_CONTRAST_THEME_ID not in serialized
        assert "theme" not in serialized.lower()

        saved_path = save_project_state(tmp_path / "theme-check", window._current_project_state())
        saved_text = saved_path.read_text(encoding="utf-8")

        assert THEME_SETTINGS_KEY not in saved_text
        assert HIGH_CONTRAST_THEME_ID not in saved_text
        assert "theme" not in saved_text.lower()
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


def test_main_window_opens_points_window_and_points_window_uses_local_settings(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    workbook_path = tmp_path / "points.xlsx"
    _write_points_workbook(
        workbook_path,
        [
            ["ФИО", "Дата", "Координаты"],
            ["Мишарин Александр Витальевич", 46115, "х-5649764 y-6661612"],
            ["Педьков Михаил Иванович", "03.04.2026", "х-5649800 y-6661934"],
        ],
    )

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings, restore_last_project=False)

    try:
        tab_names = [window.workspace_tabs.tabText(index) for index in range(window.workspace_tabs.count())]
        assert tab_names == ["Предпросмотр", "Проверка", "Экспорт"]

        window.open_points_window_action.trigger()

        points_window = window._points_window
        assert isinstance(points_window, PointsWindow)
        assert points_window.windowTitle() == "Точки из Excel"

        points_window.load_excel_path(workbook_path)
        _wait_for_import(points_window)
        points_window.point_color_button.set_color("#123456")
        points_window.point_opacity.setValue(55)

        assert points_window.preview_table.rowCount() == 2
        assert points_window.preview_splitter.count() == 2
        assert points_window.preview_table.minimumHeight() >= 260
        assert points_window.error_text.minimumHeight() >= 180
        assert points_window.preview_table.item(0, 0).text() == "2"
        assert points_window.preview_table.item(0, 1).text() == "Мишарин Александр Витальевич"
        assert "Корректных точек: 2." in points_window.summary_text.toPlainText()
        assert "Ошибок нет." in points_window.error_text.toPlainText()
        assert points_window.generate_button.isEnabled()
        assert points_window.point_style() == PointStyle(color="#123456", opacity=55)
        assert points_window.output_path.text().endswith("points.kml")

        assert settings.value(LAST_EXCEL_PATH_KEY, "", str) == str(workbook_path)
        assert settings.value(POINT_COLOR_KEY, "", str) == "#123456"
        assert settings.value(POINT_OPACITY_KEY, 0, int) == 55

        assert [window.workspace_tabs.tabText(index) for index in range(window.workspace_tabs.count())] == tab_names
    finally:
        if window._points_window is not None:
            window._points_window.close()
        window.close()


def test_points_window_running_state_disables_controls_and_shows_progress(tmp_path) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    workbook_path = tmp_path / "points.xlsx"
    _write_points_workbook(
        workbook_path,
        [
            ["ФИО", "Дата", "Координаты"],
            ["Мишарин Александр Витальевич", 46115, "х-5649764 y-6661612"],
        ],
    )

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = PointsWindow(settings=settings)

    try:
        window.load_excel_path(workbook_path)
        _wait_for_import(window)
        window._last_output_path = tmp_path / "ready.kml"

        window._set_export_running(True)

        assert not window.progress.isHidden()
        assert not window.cancel_button.isHidden()
        assert not window.excel_browse_button.isEnabled()
        assert not window.excel_load_button.isEnabled()
        assert not window.output_browse_button.isEnabled()
        assert not window.point_color_button.isEnabled()
        assert not window.point_opacity.isEnabled()
        assert not window.generate_button.isEnabled()

        window._set_export_running(False)

        assert window.progress.isHidden()
        assert window.cancel_button.isHidden()
        assert window.excel_browse_button.isEnabled()
        assert window.excel_load_button.isEnabled()
        assert window.output_browse_button.isEnabled()
        assert window.point_color_button.isEnabled()
        assert window.point_opacity.isEnabled()
        assert window.generate_button.isEnabled()
        assert window.open_output_folder_button.isEnabled()
    finally:
        window.close()

def test_points_window_import_runs_in_background_and_blocks_close(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app

    header_fio = "".join(chr(code) for code in (1060, 1048, 1054))
    header_date = "".join(chr(code) for code in (1044, 1072, 1090, 1072))
    header_coordinates = "".join(chr(code) for code in (1050, 1086, 1086, 1088, 1076, 1080, 1085, 1072, 1090, 1099))

    workbook_path = tmp_path / "points.xlsx"
    _write_points_workbook(
        workbook_path,
        [
            [header_fio, header_date, header_coordinates],
            ["Point 1", 46115, "x=-5649764 y=-6661612"],
        ],
    )

    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = PointsWindow(settings=settings)

    started = threading.Event()
    release_import = threading.Event()
    real_import = points_window_module.import_points_from_excel

    def delayed_import(path):
        started.set()
        assert release_import.wait(2.0)
        return real_import(path)

    monkeypatch.setattr(points_window_module, "import_points_from_excel", delayed_import)

    warnings: list[str] = []

    def fake_warning(_parent, _title, text, *args, **kwargs):
        warnings.append(text)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(points_window_module.QMessageBox, "warning", fake_warning)

    class DummyCloseEvent:
        def __init__(self) -> None:
            self.ignored = False

        def ignore(self) -> None:
            self.ignored = True

    timer = threading.Timer(0.4, release_import.set)
    timer.start()

    try:
        started_at = time.perf_counter()
        window.load_excel_path(workbook_path)
        elapsed = time.perf_counter() - started_at

        assert elapsed < 0.2
        _wait_until(lambda: started.is_set() and window._import_thread is not None)

        assert not window.progress.isHidden()
        assert window.progress.minimum() == 0
        assert window.progress.maximum() == 0
        assert window.cancel_button.isHidden()
        assert not window.excel_path.isEnabled()
        assert not window.excel_browse_button.isEnabled()
        assert not window.excel_load_button.isEnabled()
        assert not window.output_path.isEnabled()
        assert not window.output_browse_button.isEnabled()
        assert not window.point_color_button.isEnabled()
        assert not window.point_opacity.isEnabled()
        assert not window.generate_button.isEnabled()
        assert "Excel" in window.status_label.text()

        close_event = DummyCloseEvent()
        window.closeEvent(close_event)

        assert close_event.ignored is True
        assert len(warnings) == 1
        assert "Excel" in warnings[0]

        _wait_for_import(window)

        assert window.progress.isHidden()
        assert window.excel_path.isEnabled()
        assert window.excel_browse_button.isEnabled()
        assert window.excel_load_button.isEnabled()
        assert window.output_path.isEnabled()
        assert window.output_browse_button.isEnabled()
        assert window.point_color_button.isEnabled()
        assert window.point_opacity.isEnabled()
        assert window.generate_button.isEnabled()
        assert window.preview_table.rowCount() == 1
        assert window.preview_table.item(0, 0).text() == "2"
        assert window.preview_table.item(0, 1).text() == "Point 1"
        assert window.output_path.text().endswith("points.kml")
    finally:
        timer.cancel()
        release_import.set()
        _wait_for_import(window)
        window.close()


def test_points_window_import_failure_logs_traceback_and_shows_log_path(tmp_path, monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    _ = app
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = PointsWindow(settings=settings)
    log_directory = tmp_path / "runtime-logs"
    monkeypatch.setattr(runtime_module, "resolve_log_directory", lambda: log_directory)
    log_path = runtime_module.configure_runtime_logging()

    def broken_import(_path):
        raise ValueError("Broken workbook")

    warnings: list[str] = []

    def fake_warning(_parent, _title, text, *args, **kwargs):
        warnings.append(text)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(points_window_module, "import_points_from_excel", broken_import)
    monkeypatch.setattr(points_window_module.QMessageBox, "warning", fake_warning)

    try:
        window.load_excel_path(tmp_path / "broken.xlsx")
        _wait_for_import(window)

        assert len(warnings) == 1
        assert "Broken workbook" in warnings[0]
        assert str(log_path) in warnings[0]
        assert window.status_label.text() == "Импорт не выполнен"
        assert "Broken workbook" in window.error_text.toPlainText()

        for handler in runtime_module.get_runtime_logger().handlers:
            handler.flush()
        log_text = log_path.read_text(encoding="utf-8")

        assert "Point import worker failed." in log_text
        assert "Traceback" in log_text
        assert "ValueError: Broken workbook" in log_text
    finally:
        _wait_for_import(window)
        window.close()
