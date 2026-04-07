from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, QThread, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QAction, QColor, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from limuzin_grid_manager.app.exporter import ExportCancelled, check_free_space_for_export, export_grid, parse_meter
from limuzin_grid_manager.app.export_formats import (
    available_export_formats,
    default_export_directory,
    export_format_for_mode,
    format_export_summary,
    normalize_export_filename,
    output_path_for,
)
from limuzin_grid_manager.app.project import (
    PROJECT_DIALOG_FILTER,
    CoordinateState,
    ProjectFileError,
    ProjectState,
    apply_project_preset,
    available_project_presets,
    default_project_state,
    load_project_state,
    normalize_project_path,
    save_project_state,
)
from limuzin_grid_manager.app.resources import resource_path
from limuzin_grid_manager.core.geometry import normalize_bounds
from limuzin_grid_manager.core.models import (
    BigTileFillMode,
    Bounds,
    DEFAULT_BIG_FILL_PALETTE,
    ExportMode,
    GridOptions,
    GridStats,
    KmlStyle,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
    normalize_rgb_color,
)
from limuzin_grid_manager.core.stats import calculate_grid_stats, estimate_export_placemarks, estimate_export_size_bytes
from limuzin_grid_manager.ui.preview import GridPreviewWidget


MAX_BIG_TILE_DIALOG_ROWS = 5_000
SETTINGS_ORGANIZATION = "limuzin"
SETTINGS_APPLICATION = "LIMUZIN GRID MANAGER"
LAST_PROJECT_PATH_KEY = "project/last_path"


class ExportWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)
    cancelled = Signal(str)
    progress = Signal(int, int)

    def __init__(self, out_path: Path, bounds: Bounds, options: GridOptions) -> None:
        super().__init__()
        self._out_path = out_path
        self._bounds = bounds
        self._options = options
        self._cancel_requested = False

    @Slot()
    def run(self) -> None:
        try:
            export_grid(
                self._out_path,
                self._bounds,
                self._options,
                progress=self.progress.emit,
                cancelled=self.is_cancel_requested,
            )
        except ExportCancelled as exc:
            self.cancelled.emit(str(exc))
        except Exception as exc:
            self.failed.emit(str(exc))
        else:
            self.finished.emit(str(self._out_path))

    def cancel(self) -> None:
        self._cancel_requested = True

    def is_cancel_requested(self) -> bool:
        return self._cancel_requested


class BigTileNamesDialog(QDialog):
    def __init__(self, big_numbers: list[int], names: dict[int, str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Имена квадратов")
        self.resize(620, 520)

        layout = QVBoxLayout(self)

        note = QLabel(
            "Пустое имя оставляет стандартное название. Переименование не меняет номера 100x100 внутри квадрата."
        )
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)

        self.table = QTableWidget(len(big_numbers), 3, self)
        self.table.setHorizontalHeaderLabels(["Номер", "Пользовательское имя", "Сброс"])
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        for row, number in enumerate(big_numbers):
            number_item = QTableWidgetItem(f"{number:03d}")
            number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, number_item)
            self.table.setItem(row, 1, QTableWidgetItem(names.get(number, "")))

            reset_button = QPushButton("Сброс")
            reset_button.clicked.connect(lambda _checked=False, row=row: self._clear_name(row))
            self.table.setCellWidget(row, 2, reset_button)

        layout.addWidget(self.table, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def names(self) -> dict[int, str]:
        result: dict[int, str] = {}
        for row in range(self.table.rowCount()):
            number_item = self.table.item(row, 0)
            name_item = self.table.item(row, 1)
            if number_item is None or name_item is None:
                continue
            name = name_item.text().strip()
            if name:
                result[int(number_item.text())] = name
        return result

    def _clear_name(self, row: int) -> None:
        item = self.table.item(row, 1)
        if item is not None:
            item.setText("")


class ColorButton(QPushButton):
    colorChanged = Signal(str)

    def __init__(self, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = "#000000"
        self.clicked.connect(self._pick_color)
        self.set_color(color)

    def color(self) -> str:
        return self._color

    def set_color(self, color: str) -> None:
        self._color = normalize_rgb_color(color)
        self.setText(self._color.upper())
        self.setStyleSheet(_color_button_stylesheet(self._color))

    def _pick_color(self) -> None:
        color = QColorDialog.getColor(QColor(self._color), self, "Выберите цвет")
        if color.isValid():
            self.set_color(color.name())
            self.colorChanged.emit(self._color)


class OptionalColorButton(QPushButton):
    colorChanged = Signal()

    def __init__(self, color: str | None, fallback_color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = normalize_rgb_color(color) if color else None
        self._fallback_color = normalize_rgb_color(fallback_color)
        self.clicked.connect(self._pick_color)
        self._refresh()

    def color(self) -> str | None:
        return self._color

    def set_fallback_color(self, color: str) -> None:
        self._fallback_color = normalize_rgb_color(color)
        self._refresh()

    def clear_color(self) -> None:
        self._color = None
        self._refresh()
        self.colorChanged.emit()

    def _pick_color(self) -> None:
        initial = QColor(self._color or self._fallback_color)
        color = QColorDialog.getColor(initial, self, "Выберите цвет квадрата")
        if color.isValid():
            self._color = normalize_rgb_color(color.name())
            self._refresh()
            self.colorChanged.emit()

    def _refresh(self) -> None:
        if self._color:
            self.setText(self._color.upper())
            self.setStyleSheet(_color_button_stylesheet(self._color))
        else:
            self.setText("Общий цвет")
            self.setToolTip(f"Используется общий цвет {self._fallback_color.upper()}.")
            self.setStyleSheet(
                "QPushButton { background: #f2f4f8; color: #222; border: 1px solid #b8bec8; }"
            )


class KmlStyleDialog(QDialog):
    def __init__(self, style: KmlStyle, big_numbers: list[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Стиль KML")
        self.resize(720, 740)

        style = style.normalized()
        self._big_numbers = big_numbers
        self._palette = tuple(style.big_fill_palette) or DEFAULT_BIG_FILL_PALETTE
        self._initial_custom_colors = dict(style.custom_big_fill_colors)
        self._custom_color_buttons: list[OptionalColorButton] = []

        layout = QVBoxLayout(self)

        note = QLabel(
            "Линии применяются ко всем квадратам. Заливка 100x100 применяется к каждому малому квадрату, "
            "но цвет и прозрачность задаются одной общей настройкой."
        )
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addWidget(self._build_lines_group(style))
        layout.addWidget(self._build_small_fill_group(style))
        layout.addWidget(self._build_fill_group(style), 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._sync_fill_controls()

    def kml_style(self) -> KmlStyle:
        custom_colors = dict(self._initial_custom_colors)
        for row in range(self.custom_palette_table.rowCount()):
            number_item = self.custom_palette_table.item(row, 0)
            button = self.custom_palette_table.cellWidget(row, 1)
            if number_item is None or not isinstance(button, OptionalColorButton):
                continue
            number = int(number_item.text())
            color = button.color()
            if color:
                custom_colors[number] = color
            else:
                custom_colors.pop(number, None)

        return KmlStyle(
            big_line_color=self.big_line_color.color(),
            small_line_color=self.small_line_color.color(),
            big_line_width=self.big_line_width.value(),
            small_line_width=self.small_line_width.value(),
            big_fill_mode=BigTileFillMode(self.fill_mode.currentData()),
            big_fill_color=self.fill_color.color(),
            big_fill_opacity=self.fill_opacity.value(),
            big_fill_palette=self._palette,
            custom_big_fill_colors=tuple(sorted(custom_colors.items())),
            small_fill_enabled=self.small_fill_enabled.isChecked(),
            small_fill_color=self.small_fill_color.color(),
            small_fill_opacity=self.small_fill_opacity.value(),
        ).normalized()

    def _build_lines_group(self, style: KmlStyle) -> QGroupBox:
        group = QGroupBox("Линии")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(10)
        layout.setVerticalSpacing(8)

        self.big_line_color = ColorButton(style.big_line_color)
        self.small_line_color = ColorButton(style.small_line_color)
        self.big_line_width = self._width_spin(style.big_line_width)
        self.small_line_width = self._width_spin(style.small_line_width)

        layout.addWidget(QLabel("1000x1000: цвет"), 0, 0)
        layout.addWidget(self.big_line_color, 0, 1)
        layout.addWidget(QLabel("толщина"), 0, 2)
        layout.addWidget(self.big_line_width, 0, 3)
        layout.addWidget(QLabel("100x100: цвет"), 1, 0)
        layout.addWidget(self.small_line_color, 1, 1)
        layout.addWidget(QLabel("толщина"), 1, 2)
        layout.addWidget(self.small_line_width, 1, 3)
        layout.setColumnStretch(1, 1)
        return group

    def _build_small_fill_group(self, style: KmlStyle) -> QGroupBox:
        group = QGroupBox("Заливка 100x100")
        layout = QVBoxLayout(group)

        self.small_fill_enabled = QCheckBox("Заливать все квадраты 100x100 одним цветом")
        self.small_fill_enabled.setChecked(style.small_fill_enabled)
        self.small_fill_enabled.toggled.connect(self._sync_small_fill_controls)
        layout.addWidget(self.small_fill_enabled)

        controls = QGridLayout()
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(8)
        layout.addLayout(controls)

        self.small_fill_color_label = QLabel("Цвет")
        self.small_fill_color = ColorButton(style.small_fill_color)
        self.small_fill_opacity_label = QLabel("Прозрачность")
        self.small_fill_opacity = QSpinBox()
        self.small_fill_opacity.setRange(0, 100)
        self.small_fill_opacity.setSuffix(" %")
        self.small_fill_opacity.setValue(style.small_fill_opacity)
        self.small_fill_opacity.setMinimumHeight(34)

        controls.addWidget(self.small_fill_color_label, 0, 0)
        controls.addWidget(self.small_fill_color, 0, 1)
        controls.addWidget(self.small_fill_opacity_label, 0, 2)
        controls.addWidget(self.small_fill_opacity, 0, 3)
        controls.setColumnStretch(1, 1)

        note = QLabel("В KML заливка прописывается в каждом малом квадрате; отдельных настроек для каждого 100x100 нет.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)

        self._sync_small_fill_controls()
        return group

    def _build_fill_group(self, style: KmlStyle) -> QGroupBox:
        group = QGroupBox("Заливка 1000x1000")
        layout = QVBoxLayout(group)

        controls = QGridLayout()
        controls.setHorizontalSpacing(10)
        controls.setVerticalSpacing(8)
        layout.addLayout(controls)

        self.fill_mode = self._wide_dialog_combo()
        self.fill_mode.addItem("Без заливки", BigTileFillMode.NONE.value)
        self.fill_mode.addItem("Один цвет для всех 1000x1000", BigTileFillMode.SINGLE.value)
        self.fill_mode.addItem("Палитра по номерам", BigTileFillMode.BY_NUMBER.value)
        self.fill_mode.addItem("Пользовательская палитра", BigTileFillMode.CUSTOM.value)
        _select_combo_data(self.fill_mode, style.big_fill_mode.value)
        self.fill_mode.currentIndexChanged.connect(self._sync_fill_controls)

        self.fill_color_label = QLabel("Общий цвет")
        self.fill_color = ColorButton(style.big_fill_color)
        self.fill_color.colorChanged.connect(self._on_fill_color_changed)

        self.fill_opacity_label = QLabel("Прозрачность")
        self.fill_opacity = QSpinBox()
        self.fill_opacity.setRange(0, 100)
        self.fill_opacity.setSuffix(" %")
        self.fill_opacity.setValue(style.big_fill_opacity)
        self.fill_opacity.setMinimumHeight(34)

        controls.addWidget(QLabel("Режим"), 0, 0)
        controls.addWidget(self.fill_mode, 0, 1, 1, 3)
        controls.addWidget(self.fill_color_label, 1, 0)
        controls.addWidget(self.fill_color, 1, 1)
        controls.addWidget(self.fill_opacity_label, 1, 2)
        controls.addWidget(self.fill_opacity, 1, 3)
        controls.setColumnStretch(1, 1)

        self.palette_preview = QLabel(_palette_preview_html(self._palette))
        self.palette_preview.setTextFormat(Qt.TextFormat.RichText)
        self.palette_preview.setWordWrap(True)
        layout.addWidget(self.palette_preview)

        self.custom_palette_note = QLabel(
            "Нажмите цвет у нужного квадрата. Если цвет не задан, используется общий цвет."
        )
        self.custom_palette_note.setObjectName("Hint")
        self.custom_palette_note.setWordWrap(True)
        layout.addWidget(self.custom_palette_note)

        self.no_big_tiles_note = QLabel(
            "Пользовательская палитра по квадратам появится после корректного расчета сетки 1000x1000."
        )
        self.no_big_tiles_note.setObjectName("Hint")
        self.no_big_tiles_note.setWordWrap(True)
        layout.addWidget(self.no_big_tiles_note)

        self.custom_palette_table = QTableWidget(len(self._big_numbers), 3, self)
        self.custom_palette_table.setHorizontalHeaderLabels(["Номер", "Цвет", "Сброс"])
        self.custom_palette_table.setAlternatingRowColors(True)
        self.custom_palette_table.verticalHeader().setVisible(False)
        self.custom_palette_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.custom_palette_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.custom_palette_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        for row, number in enumerate(self._big_numbers):
            number_item = QTableWidgetItem(f"{number:03d}")
            number_item.setFlags(number_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.custom_palette_table.setItem(row, 0, number_item)

            color_button = OptionalColorButton(self._initial_custom_colors.get(number), style.big_fill_color)
            self._custom_color_buttons.append(color_button)
            self.custom_palette_table.setCellWidget(row, 1, color_button)

            reset_button = QPushButton("Общий")
            reset_button.clicked.connect(lambda _checked=False, button=color_button: button.clear_color())
            self.custom_palette_table.setCellWidget(row, 2, reset_button)

        layout.addWidget(self.custom_palette_table, 1)
        return group

    def _width_spin(self, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(1, 12)
        spin.setValue(value)
        spin.setMinimumHeight(34)
        return spin

    def _wide_dialog_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumHeight(34)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return combo

    def _sync_fill_controls(self, _index: int | None = None) -> None:
        mode = BigTileFillMode(self.fill_mode.currentData())
        fill_enabled = mode != BigTileFillMode.NONE
        uses_general_color = mode in (BigTileFillMode.SINGLE, BigTileFillMode.CUSTOM)
        uses_number_palette = mode == BigTileFillMode.BY_NUMBER
        uses_custom_palette = mode == BigTileFillMode.CUSTOM

        self.fill_color_label.setVisible(uses_general_color)
        self.fill_color.setVisible(uses_general_color)
        self.fill_opacity_label.setVisible(fill_enabled)
        self.fill_opacity.setVisible(fill_enabled)
        self.palette_preview.setVisible(uses_number_palette)
        self.custom_palette_note.setVisible(uses_custom_palette and bool(self._big_numbers))
        self.custom_palette_table.setVisible(uses_custom_palette and bool(self._big_numbers))
        self.no_big_tiles_note.setVisible(uses_custom_palette and not self._big_numbers)

    def _on_fill_color_changed(self, color: str) -> None:
        for button in self._custom_color_buttons:
            button.set_fallback_color(color)

    def _sync_small_fill_controls(self, _checked: bool | None = None) -> None:
        enabled = self.small_fill_enabled.isChecked()
        self.small_fill_color_label.setEnabled(enabled)
        self.small_fill_color.setEnabled(enabled)
        self.small_fill_opacity_label.setEnabled(enabled)
        self.small_fill_opacity.setEnabled(enabled)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None, restore_last_project: bool = True) -> None:
        super().__init__()
        self.setWindowTitle("LIMUZIN GRID MANAGER")
        icon_path = resource_path("icon.ico")
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1180, 720)
        self.setMinimumSize(1040, 620)

        self._last_output_path: Path | None = None
        self._thread: QThread | None = None
        self._worker: ExportWorker | None = None
        self._latest_stats: GridStats | None = None
        self._latest_options: GridOptions | None = None
        self._current_project_path: Path | None = None
        self._settings = settings or QSettings(SETTINGS_ORGANIZATION, SETTINGS_APPLICATION)
        self.big_tile_names: dict[int, str] = {}
        self.kml_style = KmlStyle()
        self._last_export_mode = ExportMode.KML

        self._build_menus()
        self._build_ui()
        self._connect_signals()
        self._apply_style()
        if restore_last_project:
            self._restore_last_project()
        self._schedule_stats_update()

    def _build_menus(self) -> None:
        project_menu = self.menuBar().addMenu("Проект")
        self.new_project_action = QAction("Новый проект", self)
        self.new_project_action.setShortcut("Ctrl+N")
        self.open_project_action = QAction("Открыть...", self)
        self.open_project_action.setShortcut("Ctrl+O")
        self.save_project_action = QAction("Сохранить", self)
        self.save_project_action.setShortcut("Ctrl+S")
        self.save_project_as_action = QAction("Сохранить как...", self)
        self.save_project_as_action.setShortcut("Ctrl+Shift+S")

        project_menu.addAction(self.new_project_action)
        project_menu.addAction(self.open_project_action)
        project_menu.addSeparator()
        project_menu.addAction(self.save_project_action)
        project_menu.addAction(self.save_project_as_action)

        preset_menu = self.menuBar().addMenu("Пресеты")
        self.preset_actions: dict[str, QAction] = {}
        for preset in available_project_presets():
            action = QAction(preset.title, self)
            action.setToolTip(preset.description)
            action.setData(preset.id)
            preset_menu.addAction(action)
            self.preset_actions[preset.id] = action

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
        root_layout.addLayout(self._build_project_bar())

        splitter = QSplitter()
        splitter.setChildrenCollapsible(False)
        root_layout.addWidget(splitter, 1)

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setMinimumWidth(460)

        left = QWidget()
        left.setMinimumWidth(430)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 12, 0)
        left_layout.setSpacing(12)
        left_scroll.setWidget(left)
        splitter.addWidget(left_scroll)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(10, 0, 0, 0)
        right_layout.setSpacing(12)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([470, 710])

        left_layout.addWidget(self._build_coordinates_group())
        left_layout.addWidget(self._build_grid_group())
        left_layout.addWidget(self._build_big_tile_names_group())
        left_layout.addWidget(self._build_kml_style_group())
        left_layout.addStretch(1)

        workspace_title = QLabel("Рабочая область")
        workspace_title.setObjectName("PanelTitle")
        right_layout.addWidget(workspace_title)

        self.workspace_tabs = QTabWidget()
        self.workspace_tabs.addTab(self._build_preview_tab(), "Предпросмотр")
        self.workspace_tabs.addTab(self._build_stats_tab(), "Проверка")
        self.workspace_tabs.addTab(self._build_export_tab(), "Экспорт")
        right_layout.addWidget(self.workspace_tabs, 1)

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

        self.cancel_export_button = QPushButton("Отменить")
        self.cancel_export_button.setVisible(False)
        footer.addWidget(self.cancel_export_button)

        footer.addStretch(1)

        self.generate_button = QPushButton("Сгенерировать")
        self.open_folder_button = QPushButton("Открыть папку")
        self.open_folder_button.setEnabled(False)

        footer.addWidget(self.generate_button)
        footer.addWidget(self.open_folder_button)

    def _build_project_bar(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.setSpacing(8)

        self.new_project_button = QPushButton("Новый")
        self.open_project_button = QPushButton("Открыть")
        self.save_project_button = QPushButton("Сохранить")
        self.save_project_as_button = QPushButton("Сохранить как")

        layout.addWidget(self.new_project_button)
        layout.addWidget(self.open_project_button)
        layout.addWidget(self.save_project_button)
        layout.addWidget(self.save_project_as_button)

        self.project_status = QLabel("Новый проект")
        self.project_status.setObjectName("Hint")
        self.project_status.setWordWrap(True)
        layout.addWidget(self.project_status, 1)

        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(300)
        for preset in available_project_presets():
            self.preset_combo.addItem(preset.title, preset.id)
        self.preset_combo.setToolTip("Пресеты меняют настройки сетки или KML-стиля, но не трогают координаты.")

        self.apply_preset_button = QPushButton("Применить пресет")
        layout.addWidget(self.preset_combo)
        layout.addWidget(self.apply_preset_button)
        return layout

    def _build_preview_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.preview_summary = QLabel("Предпросмотр появится после расчета сетки.")
        self.preview_summary.setObjectName("Hint")
        self.preview_summary.setWordWrap(True)
        layout.addWidget(self.preview_summary)

        controls = QHBoxLayout()
        controls.setSpacing(8)
        layout.addLayout(controls)

        self.preview_fit_button = QPushButton("Вписать всё")
        self.preview_focus_button = QPushButton("К выбранному")
        self.preview_focus_button.setEnabled(False)
        self.preview_zoom_out_button = QPushButton("-")
        self.preview_zoom_in_button = QPushButton("+")
        self.preview_zoom_out_button.setFixedWidth(40)
        self.preview_zoom_in_button.setFixedWidth(40)

        controls.addWidget(self.preview_fit_button)
        controls.addWidget(self.preview_focus_button)
        controls.addStretch(1)
        controls.addWidget(self.preview_zoom_out_button)
        controls.addWidget(self.preview_zoom_in_button)

        self.preview_canvas = GridPreviewWidget()
        layout.addWidget(self.preview_canvas, 1)

        hint = QLabel(
            "Колесо мыши масштабирует, перетаскивание двигает схему. "
            "Клик по 1000x1000 выбирает квадрат для детального просмотра 100x100."
        )
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return tab

    def _build_stats_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        self.stats_text = QTextEdit()
        self.stats_text.setReadOnly(True)
        self.stats_text.setMinimumHeight(330)
        self.stats_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.stats_text, 1)
        return tab

    def _build_export_tab(self) -> QWidget:
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)

        self.export_scroll_area = QScrollArea()
        self.export_scroll_area.setWidgetResizable(True)
        self.export_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.export_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.export_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab_layout.addWidget(self.export_scroll_area, 1)

        export_content = QWidget()
        export_content.setMinimumWidth(560)
        self.export_scroll_area.setWidget(export_content)

        layout = QVBoxLayout(export_content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        format_group = QGroupBox("Формат")
        format_layout = QVBoxLayout(format_group)
        self.export_format = self._wide_combo()
        for export_format in available_export_formats():
            self.export_format.addItem(export_format.title, export_format.mode.value)
        format_layout.addWidget(self._field_label("Вариант экспорта"))
        format_layout.addWidget(self.export_format)

        self.export_format_description = QLabel()
        self.export_format_description.setObjectName("Hint")
        self.export_format_description.setWordWrap(True)
        format_layout.addWidget(self.export_format_description)
        layout.addWidget(format_group)

        path_group = QGroupBox("Куда сохранить")
        path_layout = QGridLayout(path_group)
        path_layout.setHorizontalSpacing(10)
        path_layout.setVerticalSpacing(8)

        self.export_folder = QLineEdit(str(default_export_directory()))
        self.export_folder.setClearButtonEnabled(True)
        self.export_folder_button = QPushButton("Выбрать папку")

        self.export_filename = QLineEdit(export_format_for_mode(ExportMode.KML).default_filename)
        self.export_filename.setClearButtonEnabled(True)
        self.export_file_button = QPushButton("Выбрать файл")

        path_layout.addWidget(QLabel("Папка"), 0, 0)
        path_layout.addWidget(self.export_folder, 0, 1)
        path_layout.addWidget(self.export_folder_button, 0, 2)
        path_layout.addWidget(QLabel("Имя файла"), 1, 0)
        path_layout.addWidget(self.export_filename, 1, 1)
        path_layout.addWidget(self.export_file_button, 1, 2)
        path_layout.setColumnStretch(1, 1)
        layout.addWidget(path_group)

        summary_group = QGroupBox("Сводка перед экспортом")
        summary_layout = QVBoxLayout(summary_group)
        self.export_summary = QTextEdit()
        self.export_summary.setReadOnly(True)
        self.export_summary.setMinimumHeight(180)
        self.export_summary.setMinimumWidth(420)
        self.export_summary.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        summary_layout.addWidget(self.export_summary, 1)
        layout.addWidget(summary_group, 1)

        future_group = QGroupBox("Будущие форматы")
        future_layout = QVBoxLayout(future_group)
        future_note = QLabel(
            "Место для следующих вариантов: только 1000x1000, только 100x100, таблица номеров, "
            "настройки проекта и пресеты экспорта."
        )
        future_note.setObjectName("Hint")
        future_note.setWordWrap(True)
        future_layout.addWidget(future_note)
        layout.addWidget(future_group)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.export_generate_button = QPushButton("Сгенерировать выбранный экспорт")
        self.export_cancel_button = QPushButton("Отменить экспорт")
        self.export_cancel_button.setVisible(False)
        self.export_open_folder_button = QPushButton("Открыть папку результата")
        self.export_open_folder_button.setEnabled(False)
        actions.addWidget(self.export_generate_button)
        actions.addWidget(self.export_cancel_button)
        actions.addWidget(self.export_open_folder_button)
        layout.addLayout(actions)

        self._update_export_format_description()
        return tab

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

        layout.addWidget(self.include_1000)
        layout.addWidget(self.include_100)
        layout.addSpacing(4)
        layout.addWidget(self.snake_big)

        controls = QVBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(self._field_label("Округление границ"))
        self.rounding_mode = self._wide_combo()
        self.rounding_mode.addItem("Внутрь / обрезать", RoundingMode.IN.value)
        self.rounding_mode.addItem("Наружу / расширить", RoundingMode.OUT.value)
        self.rounding_mode.addItem("Без округления", RoundingMode.NONE.value)
        controls.addWidget(self.rounding_mode)

        small_title = QLabel("Нумерация 100x100")
        small_title.setObjectName("SectionTitle")
        controls.addWidget(small_title)

        controls.addWidget(self._field_label("Схема"))
        self.small_numbering_mode = self._wide_combo()
        self.small_numbering_mode.addItem("Змейка", SmallNumberingMode.SNAKE.value)
        self.small_numbering_mode.addItem("Обычная", SmallNumberingMode.LINEAR.value)
        self.small_numbering_mode.addItem("Спираль от центра наружу", SmallNumberingMode.SPIRAL_CENTER_OUT.value)
        self.small_numbering_mode.addItem("Спираль от края к центру", SmallNumberingMode.SPIRAL_EDGE_IN.value)
        self.small_numbering_mode.setToolTip("Как присваивать номера малым квадратам 100x100.")
        controls.addWidget(self.small_numbering_mode)

        self.small_numbering_direction_label = self._field_label("Направление")
        controls.addWidget(self.small_numbering_direction_label)
        self.small_numbering_direction = self._wide_combo()
        self.small_numbering_direction.addItem("По строкам", SmallNumberingDirection.BY_ROWS.value)
        self.small_numbering_direction.addItem("По колонкам", SmallNumberingDirection.BY_COLUMNS.value)
        self.small_numbering_direction.setToolTip("По строкам или по колонкам внутри сетки 100x100.")
        controls.addWidget(self.small_numbering_direction)

        self.small_spiral_direction_label = self._field_label("Направление спирали")
        controls.addWidget(self.small_spiral_direction_label)
        self.small_spiral_direction = self._wide_combo()
        self.small_spiral_direction.addItem("По часовой стрелке", SpiralDirection.CLOCKWISE.value)
        self.small_spiral_direction.addItem("Против часовой стрелки", SpiralDirection.COUNTERCLOCKWISE.value)
        self.small_spiral_direction.setToolTip("В какую сторону закручивается спираль нумерации.")
        controls.addWidget(self.small_spiral_direction)

        self.small_numbering_start_label = self._field_label("Стартовый угол")
        controls.addWidget(self.small_numbering_start_label)
        self.small_numbering_start = self._wide_combo()
        self.small_numbering_start.addItem("NW — верхний левый", StartCorner.NW.value)
        self.small_numbering_start.addItem("NE — верхний правый", StartCorner.NE.value)
        self.small_numbering_start.addItem("SW — нижний левый", StartCorner.SW.value)
        self.small_numbering_start.addItem("SE — нижний правый", StartCorner.SE.value)
        self.small_numbering_start.setToolTip("Из какого угла начинается нумерация малых квадратов.")
        controls.addWidget(self.small_numbering_start)
        self._sync_numbering_controls()

        layout.addLayout(controls)

        note = QLabel("Цвета и заливка настраиваются отдельно в блоке «Стиль KML».")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_big_tile_names_group(self) -> QGroupBox:
        group = QGroupBox("Имена квадратов")
        layout = QVBoxLayout(group)

        self.big_tile_names_summary = QLabel("Переименований нет.")
        self.big_tile_names_summary.setObjectName("Hint")
        self.big_tile_names_summary.setWordWrap(True)
        layout.addWidget(self.big_tile_names_summary)

        self.big_tile_names_button = QPushButton("Настроить имена 1000x1000")
        self.big_tile_names_button.setToolTip("Открыть таблицу пользовательских имен больших квадратов.")
        layout.addWidget(self.big_tile_names_button)

        note = QLabel("Имена применяются только к квадратам 1000x1000. Файлы ZIP остаются tile_###.kml.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _build_kml_style_group(self) -> QGroupBox:
        group = QGroupBox("Стиль KML")
        layout = QVBoxLayout(group)

        self.kml_style_summary = QLabel(_format_kml_style_summary(self.kml_style))
        self.kml_style_summary.setObjectName("Hint")
        self.kml_style_summary.setWordWrap(True)
        layout.addWidget(self.kml_style_summary)

        self.kml_style_button = QPushButton("Настроить стиль KML")
        self.kml_style_button.setToolTip("Цвета линий, толщина и заливка 1000x1000 и 100x100.")
        layout.addWidget(self.kml_style_button)

        note = QLabel("Заливка 100x100 применяется к каждому малому квадрату одним выбранным цветом.")
        note.setObjectName("Hint")
        note.setWordWrap(True)
        layout.addWidget(note)
        return group

    def _coord_edit(self, value: str) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setClearButtonEnabled(True)
        edit.setMinimumWidth(180)
        return edit

    def _wide_combo(self) -> QComboBox:
        combo = QComboBox()
        combo.setMinimumWidth(300)
        combo.setMinimumHeight(34)
        combo.setMinimumContentsLength(24)
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return combo

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        return label

    def _connect_signals(self) -> None:
        self._stats_timer = QTimer(self)
        self._stats_timer.setInterval(180)
        self._stats_timer.setSingleShot(True)
        self._stats_timer.timeout.connect(self.update_stats)

        for edit in (self.x_nw, self.y_nw, self.x_se, self.y_se):
            edit.textChanged.connect(self._schedule_stats_update)

        for widget in (self.include_1000, self.include_100, self.snake_big):
            widget.toggled.connect(self._schedule_stats_update)

        self.rounding_mode.currentIndexChanged.connect(self._schedule_stats_update)
        self.small_numbering_mode.currentIndexChanged.connect(self._on_numbering_mode_changed)
        self.small_numbering_direction.currentIndexChanged.connect(self._schedule_stats_update)
        self.small_spiral_direction.currentIndexChanged.connect(self._schedule_stats_update)
        self.small_numbering_start.currentIndexChanged.connect(self._schedule_stats_update)
        self.export_format.currentIndexChanged.connect(self._on_export_format_changed)
        self.export_folder.textChanged.connect(self._update_export_summary_from_latest)
        self.export_filename.textChanged.connect(self._update_export_summary_from_latest)
        self.export_folder_button.clicked.connect(self.choose_export_folder)
        self.export_file_button.clicked.connect(self.choose_export_file)
        self.generate_button.clicked.connect(self.generate)
        self.export_generate_button.clicked.connect(self.generate)
        self.cancel_export_button.clicked.connect(self.cancel_export)
        self.export_cancel_button.clicked.connect(self.cancel_export)
        self.big_tile_names_button.clicked.connect(self.open_big_tile_names_dialog)
        self.kml_style_button.clicked.connect(self.open_kml_style_dialog)
        self.preview_fit_button.clicked.connect(self.preview_canvas.fit_to_view)
        self.preview_focus_button.clicked.connect(self.preview_canvas.focus_selected_big_tile)
        self.preview_zoom_in_button.clicked.connect(self.preview_canvas.zoom_in)
        self.preview_zoom_out_button.clicked.connect(self.preview_canvas.zoom_out)
        self.preview_canvas.selectionChanged.connect(self._on_preview_selection_changed)
        self.open_folder_button.clicked.connect(self.open_output_folder)
        self.export_open_folder_button.clicked.connect(self.open_output_folder)
        self.new_project_action.triggered.connect(self.new_project)
        self.open_project_action.triggered.connect(self.open_project)
        self.save_project_action.triggered.connect(self.save_project)
        self.save_project_as_action.triggered.connect(self.save_project_as)
        self.new_project_button.clicked.connect(self.new_project)
        self.open_project_button.clicked.connect(self.open_project)
        self.save_project_button.clicked.connect(self.save_project)
        self.save_project_as_button.clicked.connect(self.save_project_as)
        self.apply_preset_button.clicked.connect(self.apply_selected_preset)
        for preset_id, action in self.preset_actions.items():
            action.triggered.connect(lambda _checked=False, preset_id=preset_id: self.apply_preset(preset_id))

    def _schedule_stats_update(self) -> None:
        if hasattr(self, "_stats_timer"):
            self._stats_timer.start()

    @Slot()
    def new_project(self) -> None:
        self._current_project_path = None
        self._clear_remembered_project_path()
        self._clear_last_output_path()
        self._apply_project_state(default_project_state())
        self._update_project_status()
        self.status_label.setText("Создан новый проект")

    @Slot()
    def open_project(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть проект",
            str(self._current_project_path or default_export_directory()),
            PROJECT_DIALOG_FILTER,
        )
        if not selected:
            return

        project_path = Path(selected)
        try:
            state = load_project_state(project_path)
        except ProjectFileError as exc:
            QMessageBox.critical(self, "Открыть проект", str(exc))
            return

        self._current_project_path = project_path
        self._remember_project_path(project_path)
        self._clear_last_output_path()
        self._apply_project_state(state)
        self._update_project_status()
        self.status_label.setText(f"Открыт проект: {project_path.name}")

    @Slot()
    def save_project(self) -> None:
        if self._current_project_path is None:
            self.save_project_as()
            return
        self._save_project_to_path(self._current_project_path)

    @Slot()
    def save_project_as(self) -> None:
        initial_path = self._current_project_path or (default_export_directory() / "project.lgm.json")
        selected, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить проект",
            str(initial_path),
            PROJECT_DIALOG_FILTER,
        )
        if not selected:
            return
        self._save_project_to_path(normalize_project_path(selected))

    def _save_project_to_path(self, path: Path) -> None:
        try:
            saved_path = save_project_state(path, self._current_project_state())
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Сохранить проект", f"Не удалось сохранить проект:\n{exc}")
            return

        self._current_project_path = saved_path
        self._remember_project_path(saved_path)
        self._update_project_status()
        self.status_label.setText(f"Проект сохранен: {saved_path.name}")

    @Slot()
    def apply_selected_preset(self) -> None:
        preset_id = self.preset_combo.currentData()
        if preset_id:
            self.apply_preset(str(preset_id))

    def apply_preset(self, preset_id: str) -> None:
        try:
            options = apply_project_preset(preset_id, self._current_options())
        except ValueError as exc:
            QMessageBox.warning(self, "Пресеты", str(exc))
            return

        self._apply_options(options)
        _select_combo_data(self.preset_combo, preset_id)
        self.status_label.setText("Пресет применен")

    def _current_project_state(self) -> ProjectState:
        return ProjectState(
            coordinates=CoordinateState(
                x_nw=self.x_nw.text(),
                y_nw=self.y_nw.text(),
                x_se=self.x_se.text(),
                y_se=self.y_se.text(),
            ),
            options=self._current_options(),
            export_folder=self.export_folder.text(),
            export_filename=self.export_filename.text(),
        )

    def _apply_project_state(self, state: ProjectState) -> None:
        self._with_blocked_signals(
            (
                self.x_nw,
                self.y_nw,
                self.x_se,
                self.y_se,
                self.export_folder,
                self.export_filename,
            ),
            lambda: self._set_project_fields(state),
        )
        self._apply_options(state.options)

    def _set_project_fields(self, state: ProjectState) -> None:
        self.x_nw.setText(state.coordinates.x_nw)
        self.y_nw.setText(state.coordinates.y_nw)
        self.x_se.setText(state.coordinates.x_se)
        self.y_se.setText(state.coordinates.y_se)
        self.export_folder.setText(state.export_folder)
        self.export_filename.setText(state.export_filename)

    def _apply_options(self, options: GridOptions) -> None:
        options = options.normalized()

        def apply() -> None:
            self.include_1000.setChecked(options.include_1000)
            self.include_100.setChecked(options.include_100)
            self.snake_big.setChecked(options.snake_big)
            _select_combo_data(self.rounding_mode, options.rounding_mode.value)
            _select_combo_data(self.small_numbering_mode, options.small_numbering_mode.value)
            _select_combo_data(self.small_numbering_direction, options.small_numbering_direction.value)
            _select_combo_data(self.small_spiral_direction, options.small_spiral_direction.value)
            _select_combo_data(self.small_numbering_start, options.small_numbering_start_corner.value)
            _select_combo_data(self.export_format, options.export_mode.value)

        self._with_blocked_signals(
            (
                self.include_1000,
                self.include_100,
                self.snake_big,
                self.rounding_mode,
                self.small_numbering_mode,
                self.small_numbering_direction,
                self.small_spiral_direction,
                self.small_numbering_start,
                self.export_format,
            ),
            apply,
        )

        self.big_tile_names = dict(options.big_tile_names)
        self.kml_style = options.kml_style.normalized()
        self._last_export_mode = options.export_mode
        self._sync_numbering_controls()
        self._update_export_format_description()
        self._update_kml_style_summary()
        self._schedule_stats_update()

    def _with_blocked_signals(self, widgets: tuple[QObject, ...], callback) -> None:
        previous = [(widget, widget.blockSignals(True)) for widget in widgets]
        try:
            callback()
        finally:
            for widget, was_blocked in previous:
                widget.blockSignals(was_blocked)

    def _restore_last_project(self) -> None:
        stored_path = self._settings.value(LAST_PROJECT_PATH_KEY, "", str)
        if not stored_path:
            return

        project_path = Path(stored_path).expanduser()
        if not project_path.is_file():
            self._clear_remembered_project_path()
            self.status_label.setText("Последний проект не найден")
            return

        try:
            state = load_project_state(project_path)
        except ProjectFileError as exc:
            self._clear_remembered_project_path()
            self.project_status.setToolTip(f"Не удалось открыть последний проект: {exc}")
            self.status_label.setText("Последний проект не открыт")
            return

        self._current_project_path = project_path
        self._clear_last_output_path()
        self._apply_project_state(state)
        self._update_project_status()
        self.status_label.setText(f"Открыт последний проект: {project_path.name}")

    def _remember_project_path(self, path: Path) -> None:
        self._settings.setValue(LAST_PROJECT_PATH_KEY, str(path.expanduser()))

    def _clear_remembered_project_path(self) -> None:
        self._settings.remove(LAST_PROJECT_PATH_KEY)

    def _save_current_project_reference(self) -> None:
        if self._current_project_path is None:
            self._clear_remembered_project_path()
            return
        if self._current_project_path.is_file():
            self._remember_project_path(self._current_project_path)
        else:
            self._clear_remembered_project_path()

    def _update_project_status(self) -> None:
        if self._current_project_path is None:
            self.project_status.setText("Новый проект")
            self.project_status.setToolTip("")
            self.setWindowTitle("LIMUZIN GRID MANAGER")
            return

        self.project_status.setText(f"Проект: {self._current_project_path.name}")
        self.project_status.setToolTip(str(self._current_project_path))
        self.setWindowTitle(f"LIMUZIN GRID MANAGER - {self._current_project_path.name}")

    def _clear_last_output_path(self) -> None:
        self._last_output_path = None
        self.open_folder_button.setEnabled(False)
        self.export_open_folder_button.setEnabled(False)

    def _on_numbering_mode_changed(self, _index: int | None = None) -> None:
        self._sync_numbering_controls()
        self._schedule_stats_update()

    def _on_export_format_changed(self, _index: int | None = None) -> None:
        self._sync_export_filename_suffix()
        self._update_export_format_description()
        self._schedule_stats_update()

    def _sync_numbering_controls(self) -> None:
        mode = SmallNumberingMode(self.small_numbering_mode.currentData())
        is_spiral = _small_numbering_is_spiral(mode)

        self.small_numbering_direction_label.setVisible(not is_spiral)
        self.small_numbering_direction.setVisible(not is_spiral)
        self.small_spiral_direction_label.setVisible(is_spiral)
        self.small_spiral_direction.setVisible(is_spiral)

        if is_spiral:
            self.small_numbering_start_label.setText("Якорь центра")
            self.small_numbering_start.setToolTip(
                "Для четной сетки выбирает один из центральных квадратов, например NW в сетке 10x10."
            )
        else:
            self.small_numbering_start_label.setText("Стартовый угол")
            self.small_numbering_start.setToolTip("Из какого угла начинается нумерация малых квадратов.")

    def _sync_export_filename_suffix(self) -> None:
        export_mode = ExportMode(self.export_format.currentData())
        export_format = export_format_for_mode(export_mode)
        previous_format = export_format_for_mode(self._last_export_mode)
        current_filename = self.export_filename.text().strip().strip('"')
        if not current_filename or current_filename == previous_format.default_filename:
            next_filename = export_format.default_filename
        else:
            next_filename = normalize_export_filename(current_filename, export_format)

        if next_filename != self.export_filename.text():
            self.export_filename.blockSignals(True)
            self.export_filename.setText(next_filename)
            self.export_filename.blockSignals(False)

        self._last_export_mode = export_mode
        self._update_export_summary_from_latest()

    def _update_export_format_description(self) -> None:
        export_format = export_format_for_mode(ExportMode(self.export_format.currentData()))
        self.export_format_description.setText(export_format.description)

    def _update_export_summary(self, stats: GridStats | None, options: GridOptions) -> None:
        out_path = self._current_output_path(options)
        self.export_summary.setPlainText(format_export_summary(stats, options, out_path))

    def _set_export_summary_error(self, message: str) -> None:
        try:
            options = self._current_options()
            export_format = export_format_for_mode(options.export_mode)
            out_path = self._current_output_path(options)
            self.export_summary.setPlainText(
                f"{export_format.title}\n"
                f"{export_format.description}\n"
                f"Путь: {out_path}\n\n"
                f"Экспорт сейчас недоступен:\n- {message}"
            )
        except Exception:
            self.export_summary.setPlainText(f"Экспорт сейчас недоступен:\n- {message}")

    @Slot()
    def _update_export_summary_from_latest(self) -> None:
        try:
            options = self._current_options()
            self._update_export_summary(self._latest_stats, options)
        except Exception as exc:
            self._set_export_summary_error(str(exc))

    def _current_bounds(self) -> Bounds:
        return normalize_bounds(
            parse_meter(self.x_nw.text(), "NW X"),
            parse_meter(self.y_nw.text(), "NW Y"),
            parse_meter(self.x_se.text(), "SE X"),
            parse_meter(self.y_se.text(), "SE Y"),
        )

    def _current_options(self) -> GridOptions:
        export_mode = ExportMode(self.export_format.currentData())
        return GridOptions(
            include_1000=self.include_1000.isChecked(),
            include_100=self.include_100.isChecked(),
            snake_big=self.snake_big.isChecked(),
            big_tile_names=tuple(sorted(self.big_tile_names.items())),
            small_numbering_mode=SmallNumberingMode(self.small_numbering_mode.currentData()),
            small_numbering_direction=SmallNumberingDirection(self.small_numbering_direction.currentData()),
            small_numbering_start_corner=StartCorner(self.small_numbering_start.currentData()),
            small_spiral_direction=SpiralDirection(self.small_spiral_direction.currentData()),
            rounding_mode=RoundingMode(self.rounding_mode.currentData()),
            export_mode=export_mode,
            kml_style=self.kml_style,
        )

    @Slot()
    def update_stats(self) -> None:
        try:
            bounds = self._current_bounds()
            options = self._current_options()
            stats = calculate_grid_stats(bounds, options)
            self._latest_stats = stats
            self._latest_options = options
            self.stats_text.setPlainText(_format_stats(stats, options))
            self.generate_button.setEnabled(not stats.errors and self._thread is None)
            self.export_generate_button.setEnabled(not stats.errors and self._thread is None)
            self._update_big_tile_names_summary(stats, options)
            self._update_kml_style_summary()
            self._update_preview(stats, options)
            self._update_export_summary(stats, options)
            self.status_label.setText("Есть ошибки" if stats.errors else "Готово к генерации")
        except Exception as exc:
            self._latest_stats = None
            self._latest_options = None
            self.stats_text.setPlainText(f"Ошибка ввода: {exc}")
            self.generate_button.setEnabled(False)
            self.export_generate_button.setEnabled(False)
            self.big_tile_names_button.setEnabled(False)
            self.big_tile_names_summary.setText("Имена 1000x1000 доступны после корректного расчета сетки.")
            self.preview_canvas.set_message(f"Предпросмотр недоступен: {exc}")
            self.preview_summary.setText("Предпросмотр появится после исправления координат.")
            self.preview_focus_button.setEnabled(False)
            self._set_export_summary_error(str(exc))
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

            self._sync_export_filename_suffix()
            out_path = self._current_output_path(options)
            if out_path.exists() and not self._confirm_overwrite(out_path):
                return
            check_free_space_for_export(out_path, stats, options)
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка", str(exc))
            return

        self._start_export(out_path, bounds, options)

    def _current_output_path(self, options: GridOptions) -> Path:
        export_format = export_format_for_mode(options.export_mode)
        out_path = output_path_for(self.export_folder.text(), self.export_filename.text(), export_format)
        if out_path.name in ("", ".", ".."):
            raise ValueError("Укажите имя файла для экспорта.")
        if out_path.parent.exists() and not out_path.parent.is_dir():
            raise ValueError(f"Папка экспорта не является папкой: {out_path.parent}")
        return out_path

    def _confirm_overwrite(self, out_path: Path) -> bool:
        result = QMessageBox.question(
            self,
            "Файл уже существует",
            f"Файл уже существует:\n{out_path}\n\nПерезаписать?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    @Slot()
    def choose_export_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку экспорта",
            self.export_folder.text() or str(default_export_directory()),
        )
        if selected:
            self.export_folder.setText(selected)

    @Slot()
    def choose_export_file(self) -> None:
        options = self._current_options()
        export_format = export_format_for_mode(options.export_mode)
        try:
            current_path = self._current_output_path(options)
        except Exception:
            current_path = default_export_directory() / export_format.default_filename
        selected, _ = QFileDialog.getSaveFileName(
            self,
            export_format.dialog_title,
            str(current_path),
            export_format.dialog_filter,
        )
        if not selected:
            return

        selected_path = Path(selected)
        self.export_folder.setText(str(selected_path.parent))
        self.export_filename.setText(normalize_export_filename(selected_path.name, export_format))

    @Slot()
    def open_big_tile_names_dialog(self) -> None:
        try:
            bounds = self._current_bounds()
            options = self._current_options()
            stats = calculate_grid_stats(bounds, options)
        except Exception as exc:
            QMessageBox.warning(self, "Имена квадратов", str(exc))
            return

        if stats.errors:
            QMessageBox.warning(self, "Имена квадратов", "\n".join(stats.errors))
            return
        if stats.big_grid is None:
            QMessageBox.information(self, "Имена квадратов", "Включите сетку 1000x1000, чтобы задать имена.")
            return
        if stats.big_grid.total > MAX_BIG_TILE_DIALOG_ROWS:
            QMessageBox.warning(
                self,
                "Имена квадратов",
                "В этой области слишком много квадратов 1000x1000 для таблицы имен: "
                f"{stats.big_grid.total}. Уменьшите область или разбейте ее на несколько проектов.",
            )
            return

        numbers = list(range(1, stats.big_grid.total + 1))
        dialog = BigTileNamesDialog(numbers, self.big_tile_names, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.big_tile_names = dialog.names()
            self.update_stats()

    @Slot()
    def open_kml_style_dialog(self) -> None:
        big_numbers: list[int] = []
        try:
            bounds = self._current_bounds()
            options = self._current_options()
            stats = calculate_grid_stats(bounds, options)
            if stats.big_grid is not None and not stats.errors and stats.big_grid.total <= MAX_BIG_TILE_DIALOG_ROWS:
                big_numbers = list(range(1, stats.big_grid.total + 1))
        except Exception:
            big_numbers = []

        dialog = KmlStyleDialog(self.kml_style, big_numbers, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.kml_style = dialog.kml_style()
            self._update_kml_style_summary()
            self.update_stats()

    def _update_big_tile_names_summary(self, stats: GridStats, options: GridOptions) -> None:
        if not options.include_1000:
            self.big_tile_names_button.setEnabled(False)
            self.big_tile_names_summary.setText("Включите сетку 1000x1000, чтобы задать имена.")
            return

        if stats.big_grid is None or stats.errors:
            self.big_tile_names_button.setEnabled(False)
            self.big_tile_names_summary.setText("Имена 1000x1000 доступны после корректного расчета сетки.")
            return

        renamed_count = _renamed_big_tile_count(options, stats)
        self.big_tile_names_button.setEnabled(self._thread is None)
        if renamed_count:
            self.big_tile_names_summary.setText(f"Переименовано: {renamed_count} из {stats.big_grid.total}.")
        else:
            self.big_tile_names_summary.setText(f"Переименований нет. Доступно квадратов: {stats.big_grid.total}.")

    def _update_kml_style_summary(self) -> None:
        self.kml_style_summary.setText(_format_kml_style_summary(self.kml_style))

    def _update_preview(self, stats: GridStats, options: GridOptions) -> None:
        if stats.errors:
            self.preview_canvas.set_message("Предпросмотр недоступен:\n" + "\n".join(stats.errors))
            self._update_preview_summary(stats, options)
            return

        self.preview_canvas.set_preview(stats, options)
        self._update_preview_summary(stats, options)

    def _update_preview_summary(self, stats: GridStats, options: GridOptions) -> None:
        if stats.errors:
            self.preview_summary.setText("Предпросмотр появится после исправления ошибок в расчете.")
            self.preview_focus_button.setEnabled(False)
            return

        if stats.big_grid is not None:
            selected = self.preview_canvas.selected_big_number()
            names = dict(options.big_tile_names)
            selected_text = f"Выбран квадрат {selected:03d}" if selected > 0 else "Квадрат не выбран"
            if selected > 0 and names.get(selected):
                selected_text += f": {names[selected]}"

            detail = "100x100 внутри выбранного квадрата показаны в этой же схеме."
            if not options.include_100:
                detail = "Сетка 100x100 выключена, поэтому внутри выбранного квадрата показана только рамка."

            self.preview_summary.setText(
                f"1000x1000: {stats.big_grid.rows} x {stats.big_grid.cols} = {stats.big_grid.total}. "
                f"{selected_text}. {detail}"
            )
            self.preview_focus_button.setEnabled(selected > 0)
            return

        if stats.small_grid is not None:
            self.preview_summary.setText(
                f"100x100: {stats.small_grid.rows} x {stats.small_grid.cols} = {stats.small_grid.total}. "
                f"Нумерация: {_format_small_numbering_options(options)}."
            )
            self.preview_focus_button.setEnabled(False)
            return

        self.preview_summary.setText("Включите хотя бы одну сетку, чтобы увидеть предпросмотр.")
        self.preview_focus_button.setEnabled(False)

    @Slot(int)
    def _on_preview_selection_changed(self, _number: int) -> None:
        if self._latest_stats is not None and self._latest_options is not None:
            self._update_preview_summary(self._latest_stats, self._latest_options)

    def _start_export(self, out_path: Path, bounds: Bounds, options: GridOptions) -> None:
        self._thread = QThread(self)
        self._worker = ExportWorker(out_path, bounds, options)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_export_finished)
        self._worker.failed.connect(self._on_export_failed)
        self._worker.cancelled.connect(self._on_export_cancelled)
        self._worker.progress.connect(self._on_export_progress)
        self._worker.finished.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.cancelled.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._on_export_thread_finished)

        self._set_export_running(True)
        self._thread.start()

    def _set_export_running(self, running: bool) -> None:
        self.generate_button.setEnabled(not running)
        self.export_generate_button.setEnabled(not running)
        self.big_tile_names_button.setEnabled(not running and self.include_1000.isChecked())
        self.kml_style_button.setEnabled(not running)
        for widget in (
            self.export_format,
            self.export_folder,
            self.export_filename,
            self.export_folder_button,
            self.export_file_button,
            self.new_project_button,
            self.open_project_button,
            self.save_project_button,
            self.save_project_as_button,
            self.preset_combo,
            self.apply_preset_button,
        ):
            widget.setEnabled(not running)
        for action in (
            self.new_project_action,
            self.open_project_action,
            self.save_project_action,
            self.save_project_as_action,
            *self.preset_actions.values(),
        ):
            action.setEnabled(not running)
        self.export_open_folder_button.setEnabled(not running and self._last_output_path is not None)
        self.progress.setVisible(running)
        if running:
            self.progress.setRange(0, 0)
            self.progress.setValue(0)
        self.cancel_export_button.setVisible(running)
        self.cancel_export_button.setEnabled(running)
        self.export_cancel_button.setVisible(running)
        self.export_cancel_button.setEnabled(running)
        if running:
            self.status_label.setText("Генерация...")

    @Slot(int, int)
    def _on_export_progress(self, done: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)
            self.status_label.setText(f"Генерация: {done} из {total}")

    @Slot()
    def cancel_export(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        self.cancel_export_button.setEnabled(False)
        self.export_cancel_button.setEnabled(False)
        self.status_label.setText("Отмена экспорта...")

    @Slot(str)
    def _on_export_finished(self, path_value: str) -> None:
        self._last_output_path = Path(path_value)
        self.open_folder_button.setEnabled(True)
        self.export_open_folder_button.setEnabled(True)
        self.status_label.setText(f"Готово: {self._last_output_path.name}")
        QMessageBox.information(self, "Готово", f"Файл создан:\n{path_value}")

    @Slot(str)
    def _on_export_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Ошибка экспорта", message)
        self.status_label.setText("Ошибка экспорта")

    @Slot(str)
    def _on_export_cancelled(self, message: str) -> None:
        self.status_label.setText(message)
        QMessageBox.information(self, "Экспорт отменен", "Экспорт отменен. Незавершенный временный файл удален.")

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
            QMessageBox.warning(self, "Экспорт", "Идет экспорт. Дождитесь завершения или нажмите «Отменить».")
            event.ignore()
            return
        self._save_current_project_reference()
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
            QLabel#SectionTitle {
                font-size: 11pt;
                font-weight: 700;
                margin-top: 8px;
            }
            QLabel#FieldLabel {
                color: #333;
                font-weight: 600;
                margin-top: 2px;
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
            QComboBox {
                min-height: 30px;
                padding: 5px 34px 5px 8px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px;
                border-left: 1px solid #b8bec8;
            }
            QPushButton {
                border-radius: 6px;
                padding: 8px 14px;
            }
            """
        )


def _select_combo_data(combo: QComboBox, value: str) -> None:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return


def _color_button_stylesheet(color: str) -> str:
    text_color = _contrast_text_color(color)
    return (
        "QPushButton {"
        f"background: {color};"
        f"color: {text_color};"
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


def _palette_preview_html(colors: tuple[str, ...]) -> str:
    blocks = "".join(
        f'<span style="background:{color}; border:1px solid #777;">&nbsp;&nbsp;&nbsp;&nbsp;</span> '
        for color in colors
    )
    return f"Палитра по номерам: {blocks}"


def _format_kml_style_summary(style: KmlStyle) -> str:
    style = style.normalized()
    return (
        f"Линии: 1000x1000 {style.big_line_color.upper()} / {style.big_line_width}, "
        f"100x100 {style.small_line_color.upper()} / {style.small_line_width}. "
        f"Заливка 1000x1000: {_format_big_fill_summary(style)}. "
        f"Заливка 100x100: {_format_small_fill_summary(style)}."
    )


def _format_big_fill_summary(style: KmlStyle) -> str:
    if style.big_fill_mode == BigTileFillMode.NONE:
        return "выключена"
    if style.big_fill_opacity <= 0:
        return "0%, без видимой заливки"
    if style.big_fill_mode == BigTileFillMode.SINGLE:
        return f"один цвет {style.big_fill_color.upper()}, {style.big_fill_opacity}%"
    if style.big_fill_mode == BigTileFillMode.BY_NUMBER:
        return f"палитра по номерам, {style.big_fill_opacity}%"
    custom_count = len(style.custom_big_fill_colors)
    return f"пользовательская палитра ({custom_count}), {style.big_fill_opacity}%"


def _format_small_fill_summary(style: KmlStyle) -> str:
    if not style.small_fill_enabled:
        return "выключена"
    if style.small_fill_opacity <= 0:
        return "0%, без видимой заливки"
    return f"каждый 100x100 {style.small_fill_color.upper()}, {style.small_fill_opacity}%"


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
        renamed_count = _renamed_big_tile_count(options, stats)
        if renamed_count:
            lines.append(f"Переименовано 1000x1000: {renamed_count}.")
    elif stats.small_grid is not None:
        lines.append(
            f"100x100: {stats.small_grid.rows} ряд. x {stats.small_grid.cols} кол. = "
            f"{stats.small_grid.total} квадратов."
        )

    placemark_count = estimate_export_placemarks(stats, options)
    if placemark_count > 0:
        lines.append(f"Объектов KML к записи: {placemark_count:,}.".replace(",", " "))
        lines.append(f"Оценка размера результата: около {_format_bytes(estimate_export_size_bytes(stats, options))}.")

    lines.append("")
    lines.append(f"KML-стиль: {_format_kml_style_summary(options.kml_style)}")
    if options.include_100:
        lines.append(f"Заливка 100x100: {_format_small_fill_summary(options.kml_style)}.")
        lines.append(f"Нумерация 100x100: {_format_small_numbering_options(options)}.")

    if stats.warnings:
        lines.append("")
        lines.append("Предупреждения:")
        lines.extend(f"- {warning}" for warning in stats.warnings)

    if stats.errors:
        lines.append("")
        lines.append("Ошибки:")
        lines.extend(f"- {error}" for error in stats.errors)

    return "\n".join(lines)


def _format_small_numbering_options(options: GridOptions) -> str:
    if _small_numbering_is_spiral(options.small_numbering_mode):
        return (
            f"{_small_numbering_label(options.small_numbering_mode)}, "
            f"{_spiral_direction_label(options.small_spiral_direction)}, "
            f"якорь центра {options.small_numbering_start_corner}"
        )
    return (
        f"{_small_numbering_label(options.small_numbering_mode)}, "
        f"{_small_direction_label(options.small_numbering_direction)}, "
        f"старт {options.small_numbering_start_corner}"
    )


def _renamed_big_tile_count(options: GridOptions, stats: GridStats) -> int:
    if stats.big_grid is None:
        return 0
    total = stats.big_grid.total
    return sum(1 for number, _name in options.big_tile_names if 1 <= number <= total)


def _format_bytes(value: int) -> str:
    units = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    size = float(max(0, value))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "Б":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(size)} Б"


def _small_numbering_label(mode: SmallNumberingMode) -> str:
    if mode == SmallNumberingMode.SNAKE:
        return "змейка"
    if mode == SmallNumberingMode.SPIRAL_CENTER_OUT:
        return "спираль от центра наружу"
    if mode == SmallNumberingMode.SPIRAL_EDGE_IN:
        return "спираль от края к центру"
    return "обычная"


def _small_direction_label(direction: SmallNumberingDirection) -> str:
    if direction == SmallNumberingDirection.BY_COLUMNS:
        return "по колонкам"
    return "по строкам"


def _spiral_direction_label(direction: SpiralDirection) -> str:
    if direction == SpiralDirection.COUNTERCLOCKWISE:
        return "против часовой стрелки"
    return "по часовой стрелке"


def _small_numbering_is_spiral(mode: SmallNumberingMode) -> bool:
    return mode in (SmallNumberingMode.SPIRAL_CENTER_OUT, SmallNumberingMode.SPIRAL_EDGE_IN)
