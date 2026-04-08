from __future__ import annotations

from collections.abc import Callable, Iterator
import csv
from pathlib import Path

from limuzin_grid_manager.core.crs import ck42_to_wgs84, make_transformer_for_zone
from limuzin_grid_manager.core.export_cells import (
    big_tile_number,
    big_tile_placemark_name,
    cell_zone,
    iter_grid_cells,
    iter_subcells,
    small_number_for_cell,
)
from limuzin_grid_manager.core.export_progress import ProgressTracker
from limuzin_grid_manager.core.models import Bounds, GridOptions, GridStats
from limuzin_grid_manager.core.stats import ensure_exportable, estimate_export_placemarks


CSV_HEADER = (
    "layer",
    "zone",
    "big_number",
    "big_name",
    "small_number",
    "x_top",
    "x_bottom",
    "y_left",
    "y_right",
    "center_lon",
    "center_lat",
)


def write_csv_all(
    out_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    options = options.normalized()
    stats = ensure_exportable(bounds, options)
    big_tile_names = dict(options.big_tile_names)
    tracker = ProgressTracker(progress, estimate_export_placemarks(stats, options), cancelled)
    transformers: dict[int, object] = {}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";", lineterminator="\n")
        writer.writerow(CSV_HEADER)
        for row in _iter_rows(options, stats, transformers, big_tile_names):
            writer.writerow(row)
            tracker.step()
    tracker.finish()


def _iter_rows(
    options: GridOptions,
    stats: GridStats,
    transformers: dict[int, object],
    big_tile_names: dict[int, str],
) -> Iterator[tuple[object, ...]]:
    if options.include_1000:
        assert stats.big_bounds is not None
        assert stats.big_grid is not None
        for row, col, x_top, y_left in iter_grid_cells(stats.big_bounds, 1000):
            big_num = big_tile_number(row, col, stats.big_grid.cols, options.snake_big)
            big_name = big_tile_placemark_name(big_num, big_tile_names)
            zone = cell_zone(y_left, 1000)
            transformer = _transformer_for_zone(zone, transformers)
            yield _csv_row("1000x1000", zone, big_num, big_name, None, x_top, y_left, 1000, transformer)

            if options.include_100:
                for small_row, small_col, small_x_top, small_y_left in iter_subcells(x_top, y_left):
                    small_num = small_number_for_cell(small_row, small_col, 10, 10, options)
                    yield _csv_row(
                        "100x100",
                        zone,
                        big_num,
                        big_name,
                        small_num,
                        small_x_top,
                        small_y_left,
                        100,
                        transformer,
                    )
        return

    if options.include_100:
        assert stats.small_bounds is not None
        assert stats.small_grid is not None
        for row, col, x_top, y_left in iter_grid_cells(stats.small_bounds, 100):
            small_num = small_number_for_cell(row, col, stats.small_grid.rows, stats.small_grid.cols, options)
            zone = cell_zone(y_left, 100)
            transformer = _transformer_for_zone(zone, transformers)
            yield _csv_row("100x100", zone, None, None, small_num, x_top, y_left, 100, transformer)


def _csv_row(
    layer: str,
    zone: int,
    big_number: int | None,
    big_name: str | None,
    small_number: int | None,
    x_top: int,
    y_left: int,
    step: int,
    transformer: object,
) -> tuple[object, ...]:
    x_bottom = x_top - step
    y_right = y_left + step
    lon, lat = ck42_to_wgs84(x_top - step / 2, y_left + step / 2, transformer)
    return (
        layer,
        zone,
        big_number,
        big_name,
        small_number,
        x_top,
        x_bottom,
        y_left,
        y_right,
        f"{lon:.7f}",
        f"{lat:.7f}",
    )


def _transformer_for_zone(zone: int, cache: dict[int, object]) -> object:
    transformer = cache.get(zone)
    if transformer is None:
        transformer = make_transformer_for_zone(zone)
        cache[zone] = transformer
    return transformer
