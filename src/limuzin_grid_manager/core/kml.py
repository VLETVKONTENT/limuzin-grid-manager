from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import TextIO
from zipfile import ZIP_DEFLATED, ZipFile

from limuzin_grid_manager.core.crs import ck42_to_wgs84, make_transformer_for_zone
from limuzin_grid_manager.core.geometry import rect_corners_ck42, snake_index
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions
from limuzin_grid_manager.core.numbering import small_number
from limuzin_grid_manager.core.stats import ensure_exportable

LINE_COLOR = "ff000000"


def write_kml_all(
    out_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    options = options.normalized()
    stats = ensure_exportable(bounds, options)
    transformer = make_transformer_for_zone(stats.zone or 0)

    total_work = max(stats.big_grid.total if stats.big_grid else 1, 1)
    done = 0

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        _write_document_start(fh, "LIMUZIN GRID MANAGER")

        if options.include_1000:
            assert stats.big_bounds is not None
            assert stats.big_grid is not None
            step_big = 1000
            for row, col, x_top, y_left in _iter_grid_cells(stats.big_bounds, step_big):
                idx0 = snake_index(row, col, stats.big_grid.cols) if options.snake_big else row * stats.big_grid.cols + col
                big_num = idx0 + 1
                fh.write("<Folder>\n")
                fh.write(f"<name>{escape_xml(f'Квадрат {big_num:03d} (1000x1000)')}</name>\n")
                fh.write("<open>0</open>\n")
                _write_rectangle_placemark(fh, f"{big_num:03d}", x_top, y_left, step_big, 2, transformer)

                if options.include_100:
                    fh.write("<Folder><name>Сетка 100x100</name><open>0</open>\n")
                    for small_row, small_col, small_x_top, small_y_left in _iter_subcells(x_top, y_left):
                        _write_rectangle_placemark(
                            fh,
                            str(_small_number_for_cell(small_row, small_col, 10, 10, options)),
                            small_x_top,
                            small_y_left,
                            100,
                            1,
                            transformer,
                        )
                    fh.write("</Folder>\n")

                fh.write("</Folder>\n")
                done += 1
                _notify(progress, done, total_work)
        else:
            assert stats.small_bounds is not None
            assert stats.small_grid is not None
            fh.write("<Folder><name>Сетка 100x100</name><open>1</open>\n")
            for row, col, x_top, y_left in _iter_grid_cells(stats.small_bounds, 100):
                small_name = _small_number_for_cell(row, col, stats.small_grid.rows, stats.small_grid.cols, options)
                _write_rectangle_placemark(fh, str(small_name), x_top, y_left, 100, 1, transformer)
            fh.write("</Folder>\n")

        _write_document_end(fh)


def write_zip_per_big_tile(
    out_zip_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    options = options.normalized()
    if not options.include_1000:
        raise ValueError("Для ZIP-экспорта требуется включить сетку 1000x1000.")
    options = GridOptions(
        include_1000=True,
        include_100=options.include_100,
        snake_big=options.snake_big,
        small_numbering_mode=options.small_numbering_mode,
        small_numbering_direction=options.small_numbering_direction,
        small_numbering_start_corner=options.small_numbering_start_corner,
        small_spiral_direction=options.small_spiral_direction,
        rounding_mode=options.rounding_mode,
        export_mode=ExportMode.ZIP,
    )
    stats = ensure_exportable(bounds, options)
    assert stats.big_bounds is not None
    assert stats.big_grid is not None
    transformer = make_transformer_for_zone(stats.zone or 0)

    out_zip_path.parent.mkdir(parents=True, exist_ok=True)
    total = stats.big_grid.total
    done = 0
    with ZipFile(out_zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for row, col, x_top, y_left in _iter_grid_cells(stats.big_bounds, 1000):
            idx0 = snake_index(row, col, stats.big_grid.cols) if options.snake_big else row * stats.big_grid.cols + col
            big_num = idx0 + 1
            zip_file.writestr(
                f"tile_{big_num:03d}.kml",
                _tile_kml(big_num, x_top, y_left, options, transformer),
            )
            done += 1
            _notify(progress, done, total)


def escape_xml(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def fmt_coords_lonlat(coords_lonlat: list[tuple[float, float]]) -> str:
    return " ".join(f"{lon:.7f},{lat:.7f},0" for lon, lat in coords_lonlat)


def polygon_placemark(name: str, coords_lonlat_closed: list[tuple[float, float]], line_width: int) -> str:
    return f"""<Placemark>
<name>{escape_xml(name)}</name>
<Style>
<LineStyle>
<color>{LINE_COLOR}</color>
<width>{int(line_width)}</width>
</LineStyle>
<PolyStyle>
<fill>0</fill>
<outline>1</outline>
</PolyStyle>
</Style>
<Polygon>
<tessellate>1</tessellate>
<altitudeMode>clampToGround</altitudeMode>
<outerBoundaryIs>
<LinearRing>
<coordinates>{fmt_coords_lonlat(coords_lonlat_closed)}</coordinates>
</LinearRing>
</outerBoundaryIs>
</Polygon>
</Placemark>
"""


def _write_document_start(fh: TextIO, name: str) -> None:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fh.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    fh.write("<Document>\n")
    fh.write(f"<name>{escape_xml(name)}</name>\n")
    fh.write("<description><![CDATA[Generated by LIMUZIN GRID MANAGER]]></description>\n")
    fh.write("<open>1</open>\n")


def _write_document_end(fh: TextIO) -> None:
    fh.write("</Document></kml>\n")


def _write_rectangle_placemark(
    fh: TextIO,
    name: str,
    x_top: int,
    y_left: int,
    step: int,
    line_width: int,
    transformer: object,
) -> None:
    corners = rect_corners_ck42(x_top, y_left, step, step)
    coords_lonlat = [ck42_to_wgs84(x, y, transformer) for x, y in corners]
    fh.write(polygon_placemark(name, coords_lonlat, line_width))


def _tile_kml(
    big_num: int,
    x_top: int,
    y_left: int,
    options: GridOptions,
    transformer: object,
) -> str:
    lines: list[str] = []

    class ListWriter:
        def write(self, value: str) -> None:
            lines.append(value)

    writer = ListWriter()
    _write_document_start(writer, f"Квадрат {big_num:03d}")
    _write_rectangle_placemark(writer, f"{big_num:03d}", x_top, y_left, 1000, 2, transformer)
    if options.include_100:
        writer.write("<Folder><name>Сетка 100x100</name><open>0</open>\n")
        for small_row, small_col, small_x_top, small_y_left in _iter_subcells(x_top, y_left):
            small_name = _small_number_for_cell(small_row, small_col, 10, 10, options)
            _write_rectangle_placemark(writer, str(small_name), small_x_top, small_y_left, 100, 1, transformer)
        writer.write("</Folder>\n")
    _write_document_end(writer)
    return "".join(lines)


def _iter_grid_cells(bounds: Bounds, step: int) -> Iterator[tuple[int, int, int, int]]:
    rows = bounds.height_m() // step
    cols = bounds.width_m() // step
    for row in range(rows):
        x_top = bounds.x_top - row * step
        for col in range(cols):
            y_left = bounds.y_left + col * step
            yield row, col, x_top, y_left


def _iter_subcells(x_top: int, y_left: int) -> Iterator[tuple[int, int, int, int]]:
    for row in range(10):
        small_x_top = x_top - row * 100
        for col in range(10):
            small_y_left = y_left + col * 100
            yield row, col, small_x_top, small_y_left


def _notify(progress: Callable[[int, int], None] | None, done: int, total: int) -> None:
    if progress is not None:
        progress(done, total)


def _small_number_for_cell(row: int, col: int, rows: int, cols: int, options: GridOptions) -> int:
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
