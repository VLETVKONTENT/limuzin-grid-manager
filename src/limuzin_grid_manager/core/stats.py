from __future__ import annotations

from limuzin_grid_manager.core.crs import infer_gk_zone
from limuzin_grid_manager.core.geometry import count_grid, round_bounds
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions, GridSize, GridStats, RoundingMode


WARN_EXPORT_PLACEMARKS = 100_000
MAX_EXPORT_PLACEMARKS = 1_000_000
WARN_ZIP_TILE_FILES = 2_000
WARN_PREVIEW_CELLS = 80_000

KML_BYTES_PER_PLACEMARK = 1200
ZIP_BYTES_PER_PLACEMARK = 700
ZIP_BYTES_PER_TILE = 2048
EXPORT_SIZE_SAFETY_BYTES = 1_048_576


def primary_rounding_step(options: GridOptions) -> int:
    options = options.normalized()
    if options.include_1000 and not options.include_100:
        return 1000
    return 100


def calculate_grid_stats(bounds: Bounds, options: GridOptions) -> GridStats:
    options = options.normalized()
    errors: list[str] = []
    warnings: list[str] = []

    if bounds.width_m() <= 0 or bounds.height_m() <= 0:
        errors.append("Область должна иметь положительную ширину и высоту.")

    if not options.include_1000 and not options.include_100:
        errors.append("Включите сетку 1000x1000, сетку 100x100 или обе сетки.")

    if options.export_mode == ExportMode.ZIP and not options.include_1000:
        errors.append("Для ZIP-экспорта требуется включить сетку 1000x1000.")

    rounded_bounds: Bounds | None = None
    big_bounds: Bounds | None = None
    small_bounds: Bounds | None = None
    big_grid: GridSize | None = None
    small_grid: GridSize | None = None
    zone_left: int | None = None
    zone_right: int | None = None

    if not errors:
        try:
            rounded_bounds = round_bounds(bounds, primary_rounding_step(options), options.rounding_mode)
        except ValueError as exc:
            errors.append(str(exc))

    if rounded_bounds is not None:
        zone_left = infer_gk_zone(rounded_bounds.y_left)
        zone_right = infer_gk_zone(rounded_bounds.y_right)
        if zone_left != zone_right:
            errors.append(
                "Область пересекает границу зон Гаусса-Крюгера: "
                f"слева зона {zone_left}, справа зона {zone_right}. Разбейте область по зонам."
            )

        if options.include_1000:
            try:
                big_bounds = round_bounds(rounded_bounds, 1000, options.rounding_mode)
                big_rows, big_cols = count_grid(big_bounds, 1000)
                big_grid = GridSize(big_rows, big_cols)
                if big_grid.total <= 0:
                    errors.append("Нет ни одного полного квадрата 1000x1000 для экспорта.")
            except ValueError as exc:
                errors.append(str(exc))

        if options.include_100 and not options.include_1000:
            try:
                small_bounds = round_bounds(rounded_bounds, 100, options.rounding_mode)
                small_rows, small_cols = count_grid(small_bounds, 100)
                small_grid = GridSize(small_rows, small_cols)
                if small_grid.total <= 0:
                    errors.append("Нет ни одного полного квадрата 100x100 для экспорта.")
            except ValueError as exc:
                errors.append(str(exc))
        elif options.include_100 and big_grid is not None:
            small_grid = GridSize(big_grid.rows * 10, big_grid.cols * 10)

        if options.rounding_mode == RoundingMode.NONE:
            _add_unrounded_warnings(rounded_bounds, options, warnings)

        _add_large_grid_feedback(big_grid, small_grid, options, warnings, errors)

    return GridStats(
        raw_bounds=bounds,
        rounded_bounds=rounded_bounds,
        big_bounds=big_bounds,
        small_bounds=small_bounds,
        big_grid=big_grid,
        small_grid=small_grid,
        zone_left=zone_left,
        zone_right=zone_right,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


def ensure_exportable(bounds: Bounds, options: GridOptions) -> GridStats:
    stats = calculate_grid_stats(bounds, options)
    if stats.errors:
        raise ValueError("\n".join(stats.errors))
    return stats


def estimate_export_placemarks(stats: GridStats, options: GridOptions) -> int:
    options = options.normalized()
    return _estimate_export_placemarks(stats.big_grid, stats.small_grid, options)


def estimate_export_size_bytes(stats: GridStats, options: GridOptions) -> int:
    options = options.normalized()
    placemark_count = estimate_export_placemarks(stats, options)
    if placemark_count <= 0:
        return 0
    if options.export_mode == ExportMode.ZIP:
        tile_count = stats.big_grid.total if stats.big_grid is not None else 0
        return EXPORT_SIZE_SAFETY_BYTES + placemark_count * ZIP_BYTES_PER_PLACEMARK + tile_count * ZIP_BYTES_PER_TILE
    return EXPORT_SIZE_SAFETY_BYTES + placemark_count * KML_BYTES_PER_PLACEMARK


def _add_unrounded_warnings(bounds: Bounds, options: GridOptions, warnings: list[str]) -> None:
    if options.include_1000:
        if bounds.width_m() % 1000 or bounds.height_m() % 1000:
            warnings.append(
                "Границы не кратны 1000 м. При режиме без округления неполные остатки "
                "по краям не попадут в экспорт 1000x1000."
            )
    elif options.include_100:
        if bounds.width_m() % 100 or bounds.height_m() % 100:
            warnings.append(
                "Границы не кратны 100 м. При режиме без округления неполные остатки "
                "по краям не попадут в экспорт 100x100."
            )


def _add_large_grid_feedback(
    big_grid: GridSize | None,
    small_grid: GridSize | None,
    options: GridOptions,
    warnings: list[str],
    errors: list[str],
) -> None:
    placemark_count = _estimate_export_placemarks(big_grid, small_grid, options)
    if placemark_count > MAX_EXPORT_PLACEMARKS:
        errors.append(
            "Экспорт слишком большой: получится примерно "
            f"{_format_int(placemark_count)} объектов KML. Уменьшите область или разбейте ее на несколько экспортов."
        )
    elif placemark_count > WARN_EXPORT_PLACEMARKS:
        warnings.append(
            "Большой экспорт: получится примерно "
            f"{_format_int(placemark_count)} объектов KML. Генерация и открытие файла в AlpineQuest могут занять время."
        )

    if options.export_mode == ExportMode.ZIP and big_grid is not None and big_grid.total > WARN_ZIP_TILE_FILES:
        warnings.append(
            "Большой ZIP: внутри будет "
            f"{_format_int(big_grid.total)} файлов tile_###.kml. Передайте такой архив в AlpineQuest только после проверки."
        )

    preview_cells = _estimate_preview_cells(big_grid, small_grid, options)
    if preview_cells > WARN_PREVIEW_CELLS:
        warnings.append(
            "Предпросмотр для этой области будет упрощен: часть линий и подписей скрывается, "
            "чтобы интерфейс оставался отзывчивым."
        )


def _estimate_export_placemarks(
    big_grid: GridSize | None,
    small_grid: GridSize | None,
    options: GridOptions,
) -> int:
    options = options.normalized()
    total = 0
    if options.include_1000 and big_grid is not None:
        total += big_grid.total
        if options.include_100:
            total += big_grid.total * 100
    elif options.include_100 and small_grid is not None:
        total += small_grid.total
    return total


def _estimate_preview_cells(
    big_grid: GridSize | None,
    small_grid: GridSize | None,
    options: GridOptions,
) -> int:
    options = options.normalized()
    if options.include_1000 and big_grid is not None:
        return big_grid.total
    if options.include_100 and small_grid is not None:
        return small_grid.total
    return 0


def _format_int(value: int) -> str:
    return f"{value:,}".replace(",", " ")
