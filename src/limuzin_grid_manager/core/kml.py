from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TextIO
from zipfile import ZIP_DEFLATED, ZipFile

from limuzin_grid_manager.core.crs import ck42_to_wgs84, make_transformer_for_zone
from limuzin_grid_manager.core.export_cells import (
    big_tile_document_name,
    big_tile_fill_color,
    big_tile_folder_name,
    big_tile_number,
    big_tile_placemark_name,
    cell_zone,
    iter_grid_cells,
    iter_subcells,
    small_number_for_cell,
)
from limuzin_grid_manager.core.export_progress import ExportCancelled, ProgressTracker
from limuzin_grid_manager.core.geometry import rect_corners_ck42
from limuzin_grid_manager.core.models import (
    Bounds,
    ExportMode,
    GridOptions,
    KmlStyle,
    normalize_rgb_color,
)
from limuzin_grid_manager.core.stats import ensure_exportable, estimate_export_placemarks


_ProgressTracker = ProgressTracker


def write_kml_all(
    out_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    options = options.normalized()
    stats = ensure_exportable(bounds, options)
    big_tile_names = dict(options.big_tile_names)
    kml_style = options.kml_style
    tracker = _ProgressTracker(progress, estimate_export_placemarks(stats, options), cancelled)
    transformers: dict[int, object] = {}

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        _write_document_start(fh, "LIMUZIN GRID MANAGER")

        if options.include_1000:
            assert stats.big_bounds is not None
            assert stats.big_grid is not None
            step_big = 1000
            for row, col, x_top, y_left in iter_grid_cells(stats.big_bounds, step_big):
                big_num = big_tile_number(row, col, stats.big_grid.cols, options.snake_big)
                big_folder_name = big_tile_folder_name(big_num, big_tile_names)
                big_placemark_name = big_tile_placemark_name(big_num, big_tile_names)
                transformer = _transformer_for_zone(cell_zone(y_left, step_big), transformers)
                fh.write("<Folder>\n")
                fh.write(f"<name>{escape_xml(big_folder_name)}</name>\n")
                fh.write("<open>0</open>\n")
                _write_big_rectangle_placemark(
                    fh,
                    big_placemark_name,
                    big_num,
                    x_top,
                    y_left,
                    step_big,
                    transformer,
                    kml_style,
                )
                tracker.step()

                if options.include_100:
                    fh.write("<Folder><name>Сетка 100x100</name><open>0</open>\n")
                    for small_row, small_col, small_x_top, small_y_left in iter_subcells(x_top, y_left):
                        _write_small_rectangle_placemark(
                            fh,
                            str(small_number_for_cell(small_row, small_col, 10, 10, options)),
                            small_x_top,
                            small_y_left,
                            100,
                            transformer,
                            kml_style,
                        )
                        tracker.step()
                    fh.write("</Folder>\n")

                fh.write("</Folder>\n")
        else:
            assert stats.small_bounds is not None
            assert stats.small_grid is not None
            fh.write("<Folder><name>Сетка 100x100</name><open>1</open>\n")
            for row, col, x_top, y_left in iter_grid_cells(stats.small_bounds, 100):
                small_name = small_number_for_cell(row, col, stats.small_grid.rows, stats.small_grid.cols, options)
                transformer = _transformer_for_zone(cell_zone(y_left, 100), transformers)
                _write_small_rectangle_placemark(
                    fh,
                    str(small_name),
                    x_top,
                    y_left,
                    100,
                    transformer,
                    kml_style,
                )
                tracker.step()
            fh.write("</Folder>\n")

        _write_document_end(fh)
    tracker.finish()


def write_zip_per_big_tile(
    out_zip_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    options = options.normalized()
    if not options.include_1000:
        raise ValueError("Для ZIP-экспорта требуется включить сетку 1000x1000.")
    options = GridOptions(
        include_1000=True,
        include_100=options.include_100,
        snake_big=options.snake_big,
        big_tile_names=options.big_tile_names,
        small_numbering_mode=options.small_numbering_mode,
        small_numbering_direction=options.small_numbering_direction,
        small_numbering_start_corner=options.small_numbering_start_corner,
        small_spiral_direction=options.small_spiral_direction,
        rounding_mode=options.rounding_mode,
        export_mode=ExportMode.ZIP,
        kml_style=options.kml_style,
    )
    stats = ensure_exportable(bounds, options)
    assert stats.big_bounds is not None
    assert stats.big_grid is not None
    big_tile_names = dict(options.big_tile_names)
    tracker = _ProgressTracker(progress, estimate_export_placemarks(stats, options), cancelled)
    transformers: dict[int, object] = {}

    out_zip_path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(out_zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for row, col, x_top, y_left in iter_grid_cells(stats.big_bounds, 1000):
            big_num = big_tile_number(row, col, stats.big_grid.cols, options.snake_big)
            transformer = _transformer_for_zone(cell_zone(y_left, 1000), transformers)
            zip_file.writestr(
                f"tile_{big_num:03d}.kml",
                _tile_kml(big_num, x_top, y_left, options, transformer, big_tile_names, tracker),
            )
    tracker.finish()


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


def polygon_placemark(
    name: str,
    coords_lonlat_closed: list[tuple[float, float]],
    line_color: str,
    line_width: int,
    fill_color: str | None = None,
    fill_opacity: int = 0,
    outline: bool = True,
) -> str:
    line_style = (
        f"""<LineStyle>
<color>{rgb_to_kml_color(line_color, 100)}</color>
<width>{int(line_width)}</width>
</LineStyle>
"""
        if outline
        else ""
    )
    poly_style = _poly_style(fill_color, fill_opacity, outline)
    return f"""<Placemark>
<name>{escape_xml(name)}</name>
<Style>
{line_style}
{poly_style}
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
    step_x: int,
    step_y: int,
    line_color: str,
    line_width: int,
    transformer: object,
    fill_color: str | None = None,
    fill_opacity: int = 0,
    outline: bool = True,
) -> None:
    corners = rect_corners_ck42(x_top, y_left, step_x, step_y)
    coords_lonlat = [ck42_to_wgs84(x, y, transformer) for x, y in corners]
    fh.write(polygon_placemark(name, coords_lonlat, line_color, line_width, fill_color, fill_opacity, outline))


def _write_big_rectangle_placemark(
    fh: TextIO,
    name: str,
    big_num: int,
    x_top: int,
    y_left: int,
    step: int,
    transformer: object,
    style: KmlStyle,
) -> None:
    _write_rectangle_placemark(
        fh,
        name,
        x_top,
        y_left,
        step,
        step,
        style.big_line_color,
        style.big_line_width,
        transformer,
        fill_color=big_tile_fill_color(big_num, style),
        fill_opacity=style.big_fill_opacity,
    )


def _write_small_rectangle_placemark(
    fh: TextIO,
    name: str,
    x_top: int,
    y_left: int,
    step: int,
    transformer: object,
    style: KmlStyle,
) -> None:
    _write_rectangle_placemark(
        fh,
        name,
        x_top,
        y_left,
        step,
        step,
        style.small_line_color,
        style.small_line_width,
        transformer,
        fill_color=style.small_fill_color if style.small_fill_enabled else None,
        fill_opacity=style.small_fill_opacity,
    )


def _tile_kml(
    big_num: int,
    x_top: int,
    y_left: int,
    options: GridOptions,
    transformer: object,
    big_tile_names: dict[int, str],
    tracker: _ProgressTracker,
) -> str:
    lines: list[str] = []

    class ListWriter:
        def write(self, value: str) -> None:
            lines.append(value)

    writer = ListWriter()
    document_name = big_tile_document_name(big_num, big_tile_names)
    placemark_name = big_tile_placemark_name(big_num, big_tile_names)
    kml_style = options.kml_style
    _write_document_start(writer, document_name)
    _write_big_rectangle_placemark(writer, placemark_name, big_num, x_top, y_left, 1000, transformer, kml_style)
    tracker.step()
    if options.include_100:
        writer.write("<Folder><name>Сетка 100x100</name><open>0</open>\n")
        for small_row, small_col, small_x_top, small_y_left in iter_subcells(x_top, y_left):
            small_name = small_number_for_cell(small_row, small_col, 10, 10, options)
            _write_small_rectangle_placemark(
                writer,
                str(small_name),
                small_x_top,
                small_y_left,
                100,
                transformer,
                kml_style,
            )
            tracker.step()
        writer.write("</Folder>\n")
    _write_document_end(writer)
    return "".join(lines)


def _transformer_for_zone(zone: int, cache: dict[int, object]) -> object:
    transformer = cache.get(zone)
    if transformer is None:
        transformer = make_transformer_for_zone(zone)
        cache[zone] = transformer
    return transformer


def _poly_style(fill_color: str | None, fill_opacity: int, outline: bool = True) -> str:
    outline_value = "1" if outline else "0"
    if fill_color is None or fill_opacity <= 0:
        return """<PolyStyle>
<fill>0</fill>
<outline>{outline}</outline>
</PolyStyle>""".format(outline=outline_value)
    return f"""<PolyStyle>
<color>{rgb_to_kml_color(fill_color, fill_opacity)}</color>
<fill>1</fill>
<outline>{outline_value}</outline>
</PolyStyle>"""


def rgb_to_kml_color(color: str, opacity_percent: int) -> str:
    rgb = normalize_rgb_color(color).removeprefix("#")
    alpha = max(0, min(255, int(max(0, min(100, int(opacity_percent))) * 255 / 100 + 0.5)))
    red = rgb[0:2]
    green = rgb[2:4]
    blue = rgb[4:6]
    return f"{alpha:02x}{blue}{green}{red}"
