from __future__ import annotations

from collections.abc import Iterator

from limuzin_grid_manager.core.geometry import snake_index
from limuzin_grid_manager.core.models import BigTileFillMode, Bounds, GridOptions, KmlStyle
from limuzin_grid_manager.core.numbering import small_number
from limuzin_grid_manager.core.zones import zone_for_y_interval


def iter_grid_cells(bounds: Bounds, step: int) -> Iterator[tuple[int, int, int, int]]:
    rows = bounds.height_m() // step
    cols = bounds.width_m() // step
    for row in range(rows):
        x_top = bounds.x_top - row * step
        for col in range(cols):
            y_left = bounds.y_left + col * step
            yield row, col, x_top, y_left


def iter_subcells(x_top: int, y_left: int) -> Iterator[tuple[int, int, int, int]]:
    for row in range(10):
        small_x_top = x_top - row * 100
        for col in range(10):
            small_y_left = y_left + col * 100
            yield row, col, small_x_top, small_y_left


def cell_zone(y_left: int, step: int) -> int:
    return zone_for_y_interval(y_left, y_left + step)


def big_tile_number(row: int, col: int, cols: int, snake_big: bool) -> int:
    idx0 = snake_index(row, col, cols) if snake_big else row * cols + col
    return idx0 + 1


def big_tile_folder_name(big_num: int, big_tile_names: dict[int, str]) -> str:
    return big_tile_names.get(big_num) or f"Квадрат {big_num:03d} (1000x1000)"


def big_tile_document_name(big_num: int, big_tile_names: dict[int, str]) -> str:
    return big_tile_names.get(big_num) or f"Квадрат {big_num:03d}"


def big_tile_placemark_name(big_num: int, big_tile_names: dict[int, str]) -> str:
    return big_tile_names.get(big_num) or f"{big_num:03d}"


def small_number_for_cell(row: int, col: int, rows: int, cols: int, options: GridOptions) -> int:
    return small_number(
        row,
        col,
        rows,
        cols,
        options.small_numbering_mode,
        options.small_numbering_direction,
        options.small_numbering_start_corner,
        options.small_spiral_direction,
    )


def big_tile_fill_color(big_num: int, style: KmlStyle) -> str | None:
    if style.big_fill_mode == BigTileFillMode.NONE or style.big_fill_opacity <= 0:
        return None
    if style.big_fill_mode == BigTileFillMode.SINGLE:
        return style.big_fill_color
    if style.big_fill_mode == BigTileFillMode.BY_NUMBER:
        return style.big_fill_palette[(big_num - 1) % len(style.big_fill_palette)]
    custom_colors = dict(style.custom_big_fill_colors)
    return custom_colors.get(big_num) or style.big_fill_color
