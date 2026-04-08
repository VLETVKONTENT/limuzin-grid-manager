from __future__ import annotations

from pathlib import Path

from limuzin_grid_manager.app.export_formats import (
    export_format_by_id,
    export_format_for_mode,
    format_export_summary,
    normalize_export_filename,
    output_path_for,
)
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions, RoundingMode
from limuzin_grid_manager.core.stats import calculate_grid_stats


def _bounds_2x2_big() -> Bounds:
    return Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_650_000, y_right=6_652_000)


def test_export_filename_normalization_tracks_selected_format() -> None:
    kml_format = export_format_for_mode(ExportMode.KML)
    zip_format = export_format_for_mode(ExportMode.ZIP)
    svg_format = export_format_by_id("svg_schema")
    geojson_format = export_format_by_id("geojson_gis")
    csv_format = export_format_by_id("csv_table")

    assert normalize_export_filename("", kml_format) == "aq_grid.kml"
    assert normalize_export_filename("custom.zip", kml_format) == "custom.kml"
    assert normalize_export_filename("custom", zip_format) == "custom.zip"
    assert normalize_export_filename("custom.kml", svg_format) == "custom.svg"
    assert normalize_export_filename("custom.svg", geojson_format) == "custom.geojson"
    assert normalize_export_filename("custom.geojson", csv_format) == "custom.csv"


def test_output_path_uses_folder_and_normalized_filename() -> None:
    export_format = export_format_for_mode(ExportMode.KML)

    assert output_path_for("C:/exports", "grid", export_format) == Path("C:/exports/grid.kml")


def test_export_summary_counts_zip_contents() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.ZIP,
    )
    stats = calculate_grid_stats(_bounds_2x2_big(), options)

    summary = format_export_summary(stats, options, Path("tiles.zip"))

    assert "Будет создан 1 ZIP-файл." in summary
    assert "Внутри архива: 4 файла tile_###.kml." in summary
    assert "Объектов KML к записи: 404." in summary
    assert "Оценка размера результата:" in summary


def test_export_summary_describes_svg_layers() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.SVG,
    )
    stats = calculate_grid_stats(_bounds_2x2_big(), options)

    summary = format_export_summary(stats, options, Path("grid.svg"))

    assert "SVG — векторная схема" in summary
    assert "Будет создан 1 SVG-файл." in summary
    assert "Объектов SVG к записи: 404." in summary
    assert "Слой 1000x1000: 4 прямоугольника." in summary
    assert "Слой 100x100 внутри больших: 400 прямоугольников." in summary


def test_export_summary_describes_geojson_features() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.GEOJSON,
    )
    stats = calculate_grid_stats(_bounds_2x2_big(), options)

    summary = format_export_summary(stats, options, Path("grid.geojson"))

    assert "GeoJSON — GIS-полигоны" in summary
    assert "Будет создан 1 GeoJSON-файл FeatureCollection." in summary
    assert "Объектов GeoJSON к записи: 404." in summary
    assert "Features 1000x1000: 4." in summary
    assert "Features 100x100 внутри больших: 400." in summary
    assert "Polygon в WGS84 lon/lat" in summary


def test_export_summary_describes_csv_rows() -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.CSV,
    )
    stats = calculate_grid_stats(_bounds_2x2_big(), options)

    summary = format_export_summary(stats, options, Path("grid.csv"))

    assert "CSV — таблица проверки" in summary
    assert "Будет создан 1 CSV-файл в UTF-8 with BOM с разделителем ;." in summary
    assert "Объектов CSV к записи: 4." in summary
    assert "Строки 1000x1000: 4." in summary
    assert "границы СК-42 и центр WGS84" in summary
