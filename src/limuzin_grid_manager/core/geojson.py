from __future__ import annotations

from collections.abc import Callable, Iterator
import json
from pathlib import Path
from typing import Any, TextIO

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
from limuzin_grid_manager.core.geometry import rect_corners_ck42
from limuzin_grid_manager.core.models import Bounds, GridOptions, GridStats
from limuzin_grid_manager.core.stats import ensure_exportable, estimate_export_placemarks


def write_geojson_all(
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
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        _write_collection_start(fh)
        first = True
        for feature in _iter_features(options, stats, transformers, big_tile_names):
            if not first:
                fh.write(",")
            fh.write("\n")
            json.dump(feature, fh, ensure_ascii=False, separators=(",", ":"))
            tracker.step()
            first = False
        _write_collection_end(fh)
    tracker.finish()


def _write_collection_start(fh: TextIO) -> None:
    fh.write('{"type":"FeatureCollection","name":"LIMUZIN GRID MANAGER","features":[')


def _write_collection_end(fh: TextIO) -> None:
    fh.write("\n]}\n")


def _iter_features(
    options: GridOptions,
    stats: GridStats,
    transformers: dict[int, object],
    big_tile_names: dict[int, str],
) -> Iterator[dict[str, Any]]:
    if options.include_1000:
        assert stats.big_bounds is not None
        assert stats.big_grid is not None
        for row, col, x_top, y_left in iter_grid_cells(stats.big_bounds, 1000):
            big_num = big_tile_number(row, col, stats.big_grid.cols, options.snake_big)
            big_name = big_tile_placemark_name(big_num, big_tile_names)
            zone = cell_zone(y_left, 1000)
            transformer = _transformer_for_zone(zone, transformers)
            yield _feature("1000x1000", zone, big_num, big_name, None, x_top, y_left, 1000, transformer)

            if options.include_100:
                for small_row, small_col, small_x_top, small_y_left in iter_subcells(x_top, y_left):
                    small_num = small_number_for_cell(small_row, small_col, 10, 10, options)
                    yield _feature(
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
            yield _feature("100x100", zone, None, None, small_num, x_top, y_left, 100, transformer)


def _feature(
    layer: str,
    zone: int,
    big_number: int | None,
    big_name: str | None,
    small_number: int | None,
    x_top: int,
    y_left: int,
    step: int,
    transformer: object,
) -> dict[str, Any]:
    x_bottom = x_top - step
    y_right = y_left + step
    return {
        "type": "Feature",
        "properties": {
            "layer": layer,
            "zone": zone,
            "cell_size_m": step,
            "big_number": big_number,
            "big_name": big_name,
            "small_number": small_number,
            "x_top": x_top,
            "x_bottom": x_bottom,
            "y_left": y_left,
            "y_right": y_right,
        },
        "geometry": {
            "type": "Polygon",
            "coordinates": [_polygon_coordinates(x_top, y_left, step, transformer)],
        },
    }


def _polygon_coordinates(x_top: int, y_left: int, step: int, transformer: object) -> list[list[float]]:
    coords = []
    for x, y in rect_corners_ck42(x_top, y_left, step, step):
        lon, lat = ck42_to_wgs84(x, y, transformer)
        coords.append([round(lon, 7), round(lat, 7)])
    return coords


def _transformer_for_zone(zone: int, cache: dict[int, object]) -> object:
    transformer = cache.get(zone)
    if transformer is None:
        transformer = make_transformer_for_zone(zone)
        cache[zone] = transformer
    return transformer
