from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from limuzin_grid_manager.app.exporter import export_grid, parse_meter
from limuzin_grid_manager.app.resources import resource_path
from limuzin_grid_manager.core.geometry import normalize_bounds
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions, GridStats, RoundingMode
from limuzin_grid_manager.core.stats import calculate_grid_stats


class ExportWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    progress = Signal(int, int)

    def __init__(self, out_path: Path, bounds: Bounds, options: GridOptions) -> None:
        super().__init__()
        self._out_path = out_path
        self._bounds = bounds
        self._options = options

    @Slot()
    def run(self) -> None:
        try:
            export_grid(self._out_path, self._bounds, self._options, progress=self.progress.emit)
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(str(self._out_path))


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LIMUZIN GRID MANAGER")
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1060, 680)
        self.setMinimumSize(920, 560)

        self._last_output_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None

        self._build_ui()
        self._connect_signals()
        self._apply_style()
        self._schedule_stats_update()

    def _build_ui(self) -> None:
        root = QWidget(self)
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        title = QLabel("LIMUZIN GRID MANAGER")
        title.setObjectName("Title")
        subtitle = QLabel("Генератор сеток KML для AlpineQuest: СК-42 / Пулково-42, Гаусс-Крюгер.")
        subtitle.setObjectName("Subtitle")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 10, 0)
        left_layout.setSpacing(12)
        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(12)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        left_layout.addWidget(self._build_coordinates_group())
        left_layout.addWidget(self._build_grid_group())
        left_layout.addWidget(self._build_export_group())
        left_layout.addStretch(1)

        stats_title = QLabel("Проверка и расчет")
        stats_title.setObjectName("PanelTitle")
        right_layout.addWidget(stats_title)

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMinimumHeight(330)
        self.stats_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.stats_text, 1)

        self.status_label = QLabel("Готово")
        self.status_label.setObjectName("Status")
        right_layout.addWidget(self.status_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root_layout.addWidget(line)

        footer = QHBoxLayout()
        root_layout.addLayout(footer)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setMinimumWidth(220)
        footer.addWidget(self.progress)

        footer.addStretch(1)

        self.check_button = QPushButton("Проверить")
        self.generate_button = QPushButton("Сгенерировать")
        self.open_folder_button = QPushButton("Открыть папку")
        self.open_folder_button.setEnabled(False)

        footer.addWidget(self.check_button)
        footer.addWidget(self.generate_button)
        footer.addWidget(self.open_folder_button)

    def _build_coordinates_group(self) -> QGroupBox:
        group = QGroupBox("Координаты, метры")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.x_nw = self._coord_edit("5660000")
        self.y_nw = self._coord_edit("6650000")
        self.x_se = self._coord_edit("5650000")
        self.y_se = self._coord_edit("6670000")

        layout.addWidget(QLabel("NW X, верх / северинг"), 0, 0)
        layout.addWidget(self.x_nw, 0, 1)
        layout.addWidget(QLabel("NW Y, лево / восток"), 1, 0)
        layout.addWidget(self.y_nw, 1, 1)
        layout.addWidget(QLabel("SE X, низ / северинг"), 2, 0)
        layout.addWidget(self.x_se, 2, 1)
        layout.addWidget(QLabel("SE Y, право / восток"), 3, 0)
        layout.addWidget(self.y_se, 3, 1)

        note = QLabel("Можно вставлять числа с пробелами и запятой: 5 660 000 или 5660000,0.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note, 4, 0, 1, 2)
        return group

    def _build_grid_group(self) -> QGroupBox:
        group = QGroupBox("Сетка")
        layout = QVBoxLayout(group)

        self.include_1000 = QCheckBox("Сетка 1000x1000")
        self.include_1000.setChecked(True)
        self.include_100 = QCheckBox("Сетка 100x100")
        self.include_100.setChecked(True)
        self.snake_big = QCheckBox("Нумерация 1000x1000 змейкой")
        self.snake_big.setChecked(True)
        self.snake_small = QCheckBox("Нумерация 100x100 змейкой")
        self.snake_small.setChecked(True)

        layout.addWidget(self.include_1000)
        layout.addWidget(self.include_100)
        layout.addSpacing(4)
        layout.addWidget(self.snake_big)
        layout.addWidget(self.snake_small)

        form = QFormLayout()
        self.rounding_mode = QComboBox()
        self.rounding_mode.addItem("Внутрь / обрезать", RoundingMode.IN.value)
        self.rounding_mode.addItem("Наружу / расширить", RoundingMode.OUT.value)
        self.rounding_mode.addItem("Без округления", RoundingMode.NONE.value)
        form.addRow("Округление:", self.rounding_mode)
        layout.addLayout(form)

        note = QLabel("Заливка отключена: KML содержит только стандартные непрозрачные линии.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox("Экспорт")
        layout = QVBoxLayout(group)

        self.export_kml = QRadioButton("Один общий файл .kml")
        self.export_zip = QRadioButton("ZIP: отдельный .kml на каждый 1000x1000")
        self.export_kml.setChecked(True)
        self.export_group = QButtonGroup(self)
        self.export_group.addButton(self.export_kml)
        self.export_group.addButton(self.export_zip)

        layout.addWidget(self.export_kml)
        layout.addWidget(self.export_zip)
        return group

    def _coord_edit(self, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setClearButtonEnabled(True)
        edit.setMinimumWidth(180)
        return edit

    def _connect_signals(self) -> None:
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(180)
        self._stats_timer.setSingleShot(True)
        self._stats_timer.timeout.connect(self.update_stats)

        for edit in (self.x_nw, self.y_nw, self.x_se, self.y_se):
            edit.textChanged.connect(self._schedule_stats_update)

        for widget in (self.include_1000, self.include_100, self.snake_big, self.snake_small):
            widget.toggled.connect(self._schedule_stats_update)

        self.rounding_mode.currentIndexChanged.connect(self._schedule_stats_update)
        self.export_kml.toggled.connect(self._schedule_stats_update)
        self.check_button.clicked.connect(self.update_stats)
        self.generate_button.clicked.connect(self.generate)
        self.open_folder_button.clicked.connect(self.open_output_folder)

    def _schedule_stats_update(self) -> None:
        if hasattr(self, "_stats_timer"):
            self._stats_timer.start()

    def _current_bounds(self) -> Bounds:
        return normalize_bounds(
            parse_meter(self.x_nw.text()),
            parse_meter(self.y_nw.text()),
            parse_meter(self.x_se.text()),
            parse_meter(self.y_se.text()),
        )

    def _current_options(self) -> GridOptions:
        export_mode = ExportMode.ZIP if self.export_zip.isChecked() else ExportMode.KML
        return GridOptions(
            include_1000=self.include_1000.isChecked(),
            include_100=self.include_100.isChecked(),
            snake_big=self.snake_big.isChecked(),
            snake_small=self.snake_small.isChecked(),
            rounding_mode=RoundingMode(self.rounding_mode.currentData()),
            export_mode=export_mode,
        )

    @Slot()
    def update_stats(self) -> None:
        try:
            bounds = self._current_bounds()
            options = self._current_options()
            stats = calculate_grid_stats(bounds, options)
            self.stats_text.setPlainText(_format_stats(stats, options))
            self.generate_button.setEnabled(not stats.errors and self._thread is None)
            self.status_label.setText("Есть ошибки" if stats.errors else "Готово к генерации")
        except Exception as exc:
            self.stats_text.setPlainText(f"Ошибка ввода: {exc}")
            self.generate_button.setEnabled(False)
            self.status_label.setText("Проверьте координаты")

    @Slot()
    def generate(self) -> None:
        try:
            bounds = self._current_bounds()
            options = self._current_options()
            stats = calculate_grid_stats(bounds, options)
            if stats.errors:
                QMessageBox.warning(self, "Проверка", "\n".join(stats.errors))
                return

            out_path = self._select_output_path(options)
            if out_path is None:
                return
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return

        self._start_export(out_path, bounds, options)

    def _select_output_path(self, options: GridOptions) -> Path | None:
        if options.export_mode == ExportMode.ZIP:
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ZIP",
                "aq_grid_tiles.zip",
                "ZIP archive (*.zip)",
            )
        else:
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить KML",
                "aq_grid.kml",
                "KML file (*.kml)",
            )
        if not selected:
            return None
        return Path(selected)

    def _start_export(self, out_path: Path, bounds: Bounds, options: GridOptions) -> None:
        self._thread = QThread(self)
        self._worker = ExportWorker(out_path, bounds, options)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.failed.connect(self._on_export_failed)
        self._worker.progress.connect(self._on_export_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_export_thread_finished)

        self._set_export_running(True)
        self._thread.start()

    def _set_export_running(self, running: bool) -> None:
        self.generate_button.setEnabled(not running)
        self.check_button.setEnabled(not running)
        self.progress.setVisible(running)
        self.progress.setRange(0, 0)
        self.status_label.setText("Генерация..." if running else "Готово")

    @Slot(int, int)
    def _on_export_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.status_label.setText(f"Генерация: {done} из {total}")

    @Slot(str)
    def _on_export_finished(self, path_value: str) -> None:
        self._last_output_path = Path(path_value)
        self.open_folder_button.setEnabled(True)
        self.status_label.setText(f"Готово: {self._last_output_path.name}")
        QMessageBox.information(self, "Готово", f"Файл создан:\n{path_value}")

    @Slot(str)
    def _on_export_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Ошибка экспорта", message)
        self.status_label.setText("Ошибка экспорта")

    @Slot()
    def _on_export_thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_export_running(False)
        self.update_stats()

    @Slot()
    def open_output_folder(self) -> None:
        if self._last_output_path is None:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._last_output_path.parent)))

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._thread is not None:
            QMessageBox.warning(self, "Экспорт", "Дождитесь завершения экспорта.")
            event.ignore()
            return
        super().closeEvent(event)

    def _apply_style(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        app.setStyleSheet(
            """
            QMainWindow, QWidget {
                font-size: 10.5pt;
            }
            QLabel#Title {
                font-size: 20pt;
                font-weight: 700;
            }
            QLabel#Subtitle, QLabel#Hint, QLabel#Status {
                color: #555;
            }
            QLabel#PanelTitle {
                font-size: 13pt;
                font-weight: 700;
            }
            QGroupBox {
                font-weight: 600;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #b8bec8;
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 14px;
            }
            """
        )


def _format_stats(stats: GridStats, options: GridOptions) -> str:
    lines: list[str] = []
    raw = stats.raw_bounds
    lines.append(f"Исходная область: {raw.width_m():,} x {raw.height_m():,} м (Y x X).".replace(",", " "))

    if stats.rounded_bounds is not None:
        rounded = stats.rounded_bounds
        lines.append(
            f"После округления: {rounded.width_m():,} x {rounded.height_m():,} м.".replace(",", " ")
        )
        if stats.zone is not None:
            lines.append(f"Зона Гаусса-Крюгера: {stats.zone}.")
        elif stats.zone_left is not None and stats.zone_right is not None:
            lines.append(f"Зоны Гаусса-Крюгера: {stats.zone_left}..{stats.zone_right}.")

    if stats.big_grid is not None:
        lines.append(
            f"1000x1000: {stats.big_grid.rows} ряд. x {stats.big_grid.cols} кол. = "
            f"{stats.big_grid.total} квадратов."
        )
        if options.include_100:
            lines.append(f"100x100 внутри 1000x1000: {stats.big_grid.total * 100} квадратов.")
    elif stats.small_grid is not None:
        lines.append(
            f"100x100: {stats.small_grid.rows} ряд. x {stats.small_grid.cols} кол. = "
            f"{stats.small_grid.total} квадратов."
        )

    lines.append("")
    lines.append("KML-стиль: стандартная непрозрачная линия, заливка отключена.")

    if stats.warnings:
        lines.append("")
        lines.append("Предупреждения:")
        lines.extend(f"- {warning}" for warning in stats.warnings)

    if stats.errors:
        lines.append("")
        lines.append("Ошибки:")
        lines.extend(f"- {error}" for error in stats.errors)

    return "\n".join(lines)
