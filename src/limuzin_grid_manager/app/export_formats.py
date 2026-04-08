from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from limuzin_grid_manager.core.models import ExportMode, GridOptions, GridStats
from limuzin_grid_manager.core.stats import estimate_export_placemarks, estimate_export_size_bytes


@dataclass(frozen=True)
class ExportFormat:
    format_id: str
    title: str
    description: str
    mode: ExportMode
    extension: str
    default_filename: str
    dialog_title: str
    dialog_filter: str
    object_label: str
    requires_1000: bool = False

    @property
    def id(self) -> str:
        return self.format_id


EXPORT_FORMATS: tuple[ExportFormat, ...] = (
    ExportFormat(
        format_id="kml_all",
        title="KML — один общий файл",
        description="Один файл .kml со всей выбранной сеткой.",
        mode=ExportMode.KML,
        extension=".kml",
        default_filename="aq_grid.kml",
        dialog_title="Сохранить KML",
        dialog_filter="KML file (*.kml)",
        object_label="KML",
    ),
    ExportFormat(
        format_id="zip_big_tiles",
        title="ZIP — KML по квадратам 1000x1000",
        description="Один .zip, внутри отдельные tile_###.kml для каждого большого квадрата.",
        mode=ExportMode.ZIP,
        extension=".zip",
        default_filename="aq_grid_tiles.zip",
        dialog_title="Сохранить ZIP",
        dialog_filter="ZIP archive (*.zip)",
        object_label="KML",
        requires_1000=True,
    ),
    ExportFormat(
        format_id="svg_schema",
        title="SVG — векторная схема",
        description="Один .svg с метрической схемой сетки, слоями, подписями и стилями.",
        mode=ExportMode.SVG,
        extension=".svg",
        default_filename="aq_grid.svg",
        dialog_title="Сохранить SVG",
        dialog_filter="SVG file (*.svg)",
        object_label="SVG",
    ),
)

KNOWN_EXPORT_SUFFIXES = frozenset(export_format.extension for export_format in EXPORT_FORMATS)


def available_export_formats() -> tuple[ExportFormat, ...]:
    return EXPORT_FORMATS


def export_format_for_mode(mode: ExportMode | str) -> ExportFormat:
    export_mode = ExportMode(mode)
    for export_format in EXPORT_FORMATS:
        if export_format.mode == export_mode:
            return export_format
    raise ValueError(f"Неизвестный режим экспорта: {mode!r}.")


def export_format_by_id(format_id: str) -> ExportFormat:
    for export_format in EXPORT_FORMATS:
        if export_format.format_id == format_id:
            return export_format
    raise ValueError(f"Неизвестный формат экспорта: {format_id!r}.")


def export_format_for_id_or_mode(value: ExportMode | str) -> ExportFormat:
    text = str(value)
    for export_format in EXPORT_FORMATS:
        if export_format.format_id == text:
            return export_format
    return export_format_for_mode(text)


def default_export_directory() -> Path:
    desktop = Path.home() / "Desktop"
    return desktop if desktop.exists() else Path.home()


def normalize_export_filename(filename: str, export_format: ExportFormat) -> str:
    value = filename.strip().strip('"')
    if not value:
        return export_format.default_filename

    path = Path(value)
    suffix = path.suffix.lower()
    if suffix == export_format.extension:
        return value
    if suffix in KNOWN_EXPORT_SUFFIXES:
        return str(path.with_suffix(export_format.extension))
    return f"{value}{export_format.extension}"


def output_path_for(folder: str, filename: str, export_format: ExportFormat) -> Path:
    normalized_filename = normalize_export_filename(filename, export_format)
    file_path = Path(normalized_filename).expanduser()
    if file_path.is_absolute():
        return file_path

    folder_path = Path(folder.strip().strip('"') or default_export_directory()).expanduser()
    return folder_path / file_path


def format_export_summary(stats: GridStats | None, options: GridOptions, out_path: Path) -> str:
    export_mode = ExportMode(options.export_mode)
    export_format = export_format_for_mode(export_mode)
    lines = [
        export_format.title,
        export_format.description,
        f"Путь: {out_path}",
        "",
    ]

    if stats is None:
        lines.append("Сводка появится после корректного расчета сетки.")
        return "\n".join(lines)

    if stats.errors:
        lines.append("Экспорт сейчас недоступен:")
        lines.extend(f"- {error}" for error in stats.errors)
        return "\n".join(lines)

    placemark_count = estimate_export_placemarks(stats, options)
    if placemark_count > 0:
        lines.append(f"Объектов {export_format.object_label} к записи: {placemark_count:,}.".replace(",", " "))
        lines.append(f"Оценка размера результата: около {_format_bytes(estimate_export_size_bytes(stats, options))}.")
        lines.append("")

    if export_mode == ExportMode.ZIP:
        tile_count = stats.big_grid.total if stats.big_grid is not None else 0
        lines.append(f"Будет создан 1 ZIP-файл.")
        lines.append(f"Внутри архива: {tile_count} {_plural_files(tile_count)} tile_###.kml.")
        if options.include_100:
            lines.append("Каждый tile_###.kml содержит большой квадрат и его сетку 100x100.")
        else:
            lines.append("Каждый tile_###.kml содержит только большой квадрат 1000x1000.")
    elif export_mode == ExportMode.SVG:
        lines.append("Будет создан 1 SVG-файл.")
        if stats.big_grid is not None:
            lines.append(f"Слой 1000x1000: {stats.big_grid.total} {_plural_rectangles(stats.big_grid.total)}.")
            if options.include_100:
                small_count = stats.big_grid.total * 100
                lines.append(f"Слой 100x100 внутри больших: {small_count} {_plural_rectangles(small_count)}.")
        elif stats.small_grid is not None:
            lines.append(f"Слой 100x100: {stats.small_grid.total} {_plural_rectangles(stats.small_grid.total)}.")
        lines.append("Координаты SVG сохраняются в метрах с началом viewBox в верхнем левом углу области.")
    else:
        lines.append("Будет создан 1 общий KML-файл.")
        if stats.big_grid is not None:
            lines.append(f"Квадраты 1000x1000: {stats.big_grid.total}.")
            if options.include_100:
                lines.append(f"Квадраты 100x100 внутри больших: {stats.big_grid.total * 100}.")
        elif stats.small_grid is not None:
            lines.append(f"Квадраты 100x100: {stats.small_grid.total}.")

    if stats.warnings:
        lines.append("")
        lines.append("Предупреждения:")
        lines.extend(f"- {warning}" for warning in stats.warnings)

    return "\n".join(lines)


def _plural_files(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "файл"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "файла"
    return "файлов"


def _plural_rectangles(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "прямоугольник"
    if count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        return "прямоугольника"
    return "прямоугольников"


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
