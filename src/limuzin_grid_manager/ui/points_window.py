from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal, Slot
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from limuzin_grid_manager.app.export_formats import default_export_directory
from limuzin_grid_manager.app.point_exporter import export_points_kml
from limuzin_grid_manager.app.point_import import PointImportResult, import_points_from_excel
from limuzin_grid_manager.app.resources import resource_path
from limuzin_grid_manager.core.points import PointStyle, normalize_point_color, normalize_point_opacity


SETTINGS_ORGANIZATION = "limuzin"
SETTINGS_APPLICATION = "LIMUZIN GRID MANAGER"
LAST_EXCEL_PATH_KEY = "points/last_excel_path"
LAST_EXPORT_DIR_KEY = "points/last_export_dir"
POINT_COLOR_KEY = "points/style_color"
POINT_OPACITY_KEY = "points/style_opacity"


class PointColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = "#32ca00"
        self.clicked.connect(self._pick_color)
        self.set_color(color)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = normalize_point_color(color)
        self.setText(self._color.upper())
        self.setStyleSheet(_color_button_stylesheet(self._color))
        self.colorChanged.emit(self._color)

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Выберите цвет точек")
        if color.isValid():
            self.set_color(color.name())


class PointsWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Точки из Excel")
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1120, 760)
        self.setMinimumSize(940, 620)

        self._settings = settings or QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        self._import_result: PointImportResult | None = None

        self._build_ui()
        self._connect_signals()
        self._restore_settings()
        self._update_import_view(None)
        self._update_generate_enabled()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Точки из Excel")
        title.setObjectName("Title")
        subtitle = QLabel(
            "Отдельное окно для sample-first импорта `.xlsx` и генерации AlpineQuest-совместимого point-KML."
        )
        subtitle.setObjectName("Subtitle")
        subtitle.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(self._build_import_group())
        layout.addWidget(self._build_summary_group())
        layout.addWidget(self._build_preview_group(), 1)
        layout.addWidget(self._build_export_group())

        footer = QHBoxLayout()
        footer.setSpacing(8)
        layout.addLayout(footer)

        self.status_label = QLabel("Выберите Excel-файл для импорта.")
        self.status_label.setObjectName("Status")
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label, 1)

        self.generate_button = QPushButton("Сгенерировать KML")
        footer.addWidget(self.generate_button)

    def _build_import_group(self) -> QGroupBox:
        group = QGroupBox("Источник `.xlsx`")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.excel_path = QLineEdit()
        self.excel_path.setClearButtonEnabled(True)
        self.excel_path.setPlaceholderText("Выберите workbook с колонками ФИО | Дата | Координаты")

        self.excel_browse_button = QPushButton("Выбрать .xlsx")
        self.excel_load_button = QPushButton("Загрузить")

        layout.addWidget(QLabel("Excel-файл"), 0, 0)
        layout.addWidget(self.excel_path, 0, 1)
        layout.addWidget(self.excel_browse_button, 0, 2)
        layout.addWidget(self.excel_load_button, 0, 3)
        layout.setColumnStretch(1, 1)

        note = QLabel(
            "Импорт читает первый лист с данными и строго ожидает заголовок `ФИО | Дата | Координаты`."
        )
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note, 1, 0, 1, 4)
        return group

    def _build_summary_group(self) -> QGroupBox:
        group = QGroupBox("Сводка импорта")
        layout = QVBoxLayout(group)

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(110)
        self.summary_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.summary_text)
        return group

    def _build_preview_group(self) -> QGroupBox:
        group = QGroupBox("Предварительный просмотр и ошибки")
        layout = QVBoxLayout(group)
        layout.setSpacing(10)

        self.preview_table = QTableWidget(0, 8, self)
        self.preview_table.setHorizontalHeaderLabels(["Строка", "ФИО", "Дата", "X", "Y", "Зона", "Lon", "Lat"])
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.verticalHeader().setVisible(False)
        self.preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.preview_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for column in range(2, 8):
            self.preview_table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.preview_table, 1)

        self.error_text = QTextEdit()
        self.error_text.setReadOnly(True)
        self.error_text.setMinimumHeight(120)
        layout.addWidget(self.error_text)
        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("Экспорт point-KML")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.point_color_button = PointColorButton(PointStyle().color)
        self.point_opacity = QSpinBox()
        self.point_opacity.setRange(0, 100)
        self.point_opacity.setSuffix(" %")
        self.point_opacity.setMinimumHeight(34)

        self.output_path = QLineEdit()
        self.output_path.setClearButtonEnabled(True)
        self.output_path.setPlaceholderText("Укажите путь для итогового .kml")
        self.output_browse_button = QPushButton("Куда сохранить")

        layout.addWidget(QLabel("Цвет точек"), 0, 0)
        layout.addWidget(self.point_color_button, 0, 1)
        layout.addWidget(QLabel("Прозрачность"), 0, 2)
        layout.addWidget(self.point_opacity, 0, 3)
        layout.addWidget(QLabel("Итоговый `.kml`"), 1, 0)
        layout.addWidget(self.output_path, 1, 1, 1, 2)
        layout.addWidget(self.output_browse_button, 1, 3)
        layout.setColumnStretch(1, 1)
        return group

    def _connect_signals(self) -> None:
        self.excel_browse_button.clicked.connect(self.choose_excel_file)
        self.excel_load_button.clicked.connect(self.load_selected_excel)
        self.output_browse_button.clicked.connect(self.choose_output_path)
        self.output_path.textChanged.connect(self._on_output_path_changed)
        self.point_opacity.valueChanged.connect(self._save_style_settings)
        self.point_color_button.colorChanged.connect(self._save_style_settings)
        self.generate_button.clicked.connect(self.generate)

    def _restore_settings(self) -> None:
        last_excel_path = self._settings.value(LAST_EXCEL_PATH_KEY, "", str)
        if last_excel_path:
            self.excel_path.setText(last_excel_path)

        color = self._settings.value(POINT_COLOR_KEY, PointStyle().color, str)
        opacity = self._settings.value(POINT_OPACITY_KEY, PointStyle().opacity, int)
        self.point_color_button.set_color(color)
        self.point_opacity.setValue(normalize_point_opacity(opacity))

    def point_style(self) -> PointStyle:
        return PointStyle(
            color=self.point_color_button.color(),
            opacity=self.point_opacity.value(),
        ).normalized()

    @Slot()
    def choose_excel_file(self) -> None:
        initial = self._initial_excel_path()
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите Excel-файл с точками",
            str(initial),
            "Excel Workbook (*.xlsx)",
        )
        if not selected:
            return
        self.load_excel_path(Path(selected))

    @Slot()
    def load_selected_excel(self) -> None:
        raw_path = self.excel_path.text().strip().strip('"')
        if not raw_path:
            QMessageBox.warning(self, "Точки из Excel", "Сначала укажите путь к `.xlsx`.")
            return
        self.load_excel_path(Path(raw_path).expanduser())

    def load_excel_path(self, path: Path) -> None:
        workbook_path = Path(path).expanduser()
        self.excel_path.setText(str(workbook_path))
        try:
            result = import_points_from_excel(workbook_path)
        except ValueError as exc:
            self._import_result = None
            self._update_import_view(None, import_error=str(exc))
            self.status_label.setText("Импорт не выполнен")
            self._update_generate_enabled()
            QMessageBox.warning(self, "Импорт точек", str(exc))
            return

        self._import_result = result
        self._settings.setValue(LAST_EXCEL_PATH_KEY, str(workbook_path))
        self._settings.sync()
        if not self.output_path.text().strip():
            self.output_path.setText(str(self._suggested_output_path(workbook_path)))
        self._update_import_view(result)
        self.status_label.setText(f"Импортировано строк: {result.total_rows}. Корректных точек: {len(result.records)}.")
        self._update_generate_enabled()

    @Slot()
    def choose_output_path(self) -> None:
        initial = self._initial_output_path()
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Куда сохранить point-KML",
            str(initial),
            "KML (*.kml)",
        )
        if not selected:
            return
        selected_path = Path(selected)
        if selected_path.suffix.lower() != ".kml":
            selected_path = selected_path.with_suffix(".kml")
        self.output_path.setText(str(selected_path))

    @Slot()
    def generate(self) -> None:
        if self._import_result is None:
            QMessageBox.warning(self, "Экспорт точек", "Сначала загрузите Excel-файл.")
            return
        if not self._import_result.is_exportable:
            QMessageBox.warning(self, "Экспорт точек", "Экспорт заблокирован, пока в workbook есть ошибки строк.")
            return

        raw_output = self.output_path.text().strip().strip('"')
        if not raw_output:
            QMessageBox.warning(self, "Экспорт точек", "Укажите путь для итогового `.kml`.")
            return

        out_path = Path(raw_output).expanduser()
        if out_path.suffix.lower() != ".kml":
            out_path = out_path.with_suffix(".kml")
            self.output_path.setText(str(out_path))

        if out_path.exists():
            answer = QMessageBox.question(
                self,
                "Экспорт точек",
                f"Файл уже существует и будет перезаписан:\n{out_path}",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        try:
            self.generate_button.setEnabled(False)
            self.status_label.setText("Генерация point-KML...")
            export_points_kml(out_path, self._import_result.records, self.point_style())
        except Exception as exc:
            self.status_label.setText("Ошибка экспорта")
            QMessageBox.critical(self, "Экспорт точек", str(exc))
            self._update_generate_enabled()
            return

        self._settings.setValue(LAST_EXPORT_DIR_KEY, str(out_path.parent))
        self._save_style_settings()
        self.status_label.setText(f"Готово: {out_path.name}")
        self._update_generate_enabled()
        QMessageBox.information(self, "Экспорт точек", f"Файл создан:\n{out_path}")

    def _update_import_view(self, result: PointImportResult | None, import_error: str | None = None) -> None:
        self.preview_table.setRowCount(0)
        if result is None:
            if import_error:
                self.summary_text.setPlainText("Импорт не выполнен.")
                self.error_text.setPlainText(import_error)
            else:
                self.summary_text.setPlainText("Excel-файл еще не загружен.")
                self.error_text.setPlainText("Ошибок пока нет.")
            return

        self.summary_text.setPlainText(result.summary)
        self.error_text.setPlainText(_format_import_errors(result))

        self.preview_table.setRowCount(len(result.records))
        for row_index, record in enumerate(result.records):
            values = (
                str(record.source_row),
                record.name,
                record.display_date,
                str(record.x),
                str(record.y),
                str(record.zone),
                f"{record.lon:.8f}",
                f"{record.lat:.8f}",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row_index, column, item)
        self.preview_table.resizeRowsToContents()

    def _update_generate_enabled(self) -> None:
        self.generate_button.setEnabled(
            self._import_result is not None
            and self._import_result.is_exportable
            and bool(self.output_path.text().strip())
        )

    def _suggested_output_path(self, workbook_path: Path) -> Path:
        export_dir_value = self._settings.value(LAST_EXPORT_DIR_KEY, "", str)
        if export_dir_value:
            export_dir = Path(export_dir_value).expanduser()
            if export_dir.exists():
                return export_dir / f"{workbook_path.stem}.kml"
        return workbook_path.with_suffix(".kml")

    def _initial_excel_path(self) -> Path:
        raw_path = self.excel_path.text().strip().strip('"')
        if raw_path:
            return Path(raw_path).expanduser()
        stored_path = self._settings.value(LAST_EXCEL_PATH_KEY, "", str)
        if stored_path:
            return Path(stored_path).expanduser()
        return default_export_directory()

    def _initial_output_path(self) -> Path:
        raw_path = self.output_path.text().strip().strip('"')
        if raw_path:
            return Path(raw_path).expanduser()
        raw_dir = self._settings.value(LAST_EXPORT_DIR_KEY, "", str)
        if raw_dir:
            return Path(raw_dir).expanduser() / "points.kml"
        return default_export_directory() / "points.kml"

    @Slot()
    def _on_output_path_changed(self) -> None:
        raw_output = self.output_path.text().strip().strip('"')
        if raw_output:
            self._settings.setValue(LAST_EXPORT_DIR_KEY, str(Path(raw_output).expanduser().parent))
            self._settings.sync()
        self._update_generate_enabled()

    @Slot()
    def _save_style_settings(self) -> None:
        style = self.point_style()
        self._settings.setValue(POINT_COLOR_KEY, style.color)
        self._settings.setValue(POINT_OPACITY_KEY, style.opacity)
        self._settings.sync()


def _format_import_errors(result: PointImportResult) -> str:
    if not result.errors:
        return "Ошибок нет. Экспорт доступен."
    return "\n".join(f"Строка {error.source_row}: {error.message}" for error in result.errors)


def _color_button_stylesheet(color: str) -> str:
    return (
        "QPushButton {"
        f"background: {color};"
        f"color: {_contrast_text_color(color)};"
        "border: 1px solid #6d7480;"
        "font-weight: 700;"
        "}"
    )


def _contrast_text_color(color: str) -> str:
    rgb = color.removeprefix("#")
    red = int(rgb[0:2], 16)
    green = int(rgb[2:4], 16)
    blue = int(rgb[4:6], 16)
    luminance = (red * 299 + green * 587 + blue * 114) / 1000
    return "#111111" if luminance > 150 else "#ffffff"
