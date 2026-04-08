from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from limuzin_grid_manager.app.exporter import export_grid
from limuzin_grid_manager.core.csv_export import CSV_HEADER, write_csv_all
from limuzin_grid_manager.core.crs import ck42_to_wgs84, make_transformer_for_zone
from limuzin_grid_manager.core.geojson import write_geojson_all
from limuzin_grid_manager.core.kml import write_kml_all, write_zip_per_big_tile
from limuzin_grid_manager.core.kml import ExportCancelled
from limuzin_grid_manager.core.svg import write_svg_all
from limuzin_grid_manager.core.models import (
    BigTileFillMode,
    Bounds,
    ExportMode,
    GridOptions,
    KmlStyle,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
)


def _bounds_2x2_big() -> Bounds:
    return Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_650_000, y_right=6_652_000)


def _bounds_2x2_big_crossing_zones() -> Bounds:
    return Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_000, y_right=7_001_000)


def test_write_kml_all_is_xml_without_colored_fill(tmp_path: Path) -> None:
    out_path = tmp_path / "grid.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )

    write_kml_all(out_path, _bounds_2x2_big(), options)
    text = out_path.read_text(encoding="utf-8")
    root = ElementTree.fromstring(text)

    placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert len(placemarks) == 404
    assert "<fill>0</fill>" in text
    assert "<color>ff000000</color>" in text
    assert "7f00ff00" not in text
    assert "PolyStyle>\n<color>" not in text


def test_write_svg_all_is_xml_with_layers_and_labels(tmp_path: Path) -> None:
    out_path = tmp_path / "grid.svg"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.SVG,
    )

    write_svg_all(out_path, _bounds_2x2_big(), options)
    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))

    svg_ns = "{http://www.w3.org/2000/svg}"
    rects = root.findall(f".//{svg_ns}rect")
    labels = root.findall(f".//{svg_ns}text")

    assert root.tag == f"{svg_ns}svg"
    assert root.attrib["viewBox"] == "0 0 2000 2000"
    assert root.attrib["data-zone"] == "6"
    assert len(rects) == 404
    assert len(labels) == 404
    assert sum(1 for rect in rects if rect.attrib["data-layer"] == "1000x1000") == 4
    assert sum(1 for rect in rects if rect.attrib["data-layer"] == "100x100") == 400
    assert rects[0].attrib["data-big-number"] == "1"
    assert labels[0].text == "001"


def test_write_geojson_all_is_feature_collection_with_wgs84_properties(tmp_path: Path) -> None:
    out_path = tmp_path / "grid.geojson"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        big_tile_names=((1, "Северный участок"),),
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.GEOJSON,
    )

    write_geojson_all(out_path, _bounds_2x2_big(), options)
    data = json.loads(out_path.read_text(encoding="utf-8"))
    features = data["features"]
    first = features[0]
    first_small = features[1]
    ring = first["geometry"]["coordinates"][0]
    lon, lat = ring[0]

    assert data["type"] == "FeatureCollection"
    assert len(features) == 404
    assert first["geometry"]["type"] == "Polygon"
    assert len(ring) == 5
    assert ring[0] == ring[-1]
    assert -180 <= lon <= 180
    assert -90 <= lat <= 90
    assert first["properties"] == {
        "layer": "1000x1000",
        "zone": 6,
        "cell_size_m": 1000,
        "big_number": 1,
        "big_name": "Северный участок",
        "small_number": None,
        "x_top": 5_662_000,
        "x_bottom": 5_661_000,
        "y_left": 6_650_000,
        "y_right": 6_651_000,
    }
    assert first_small["properties"]["layer"] == "100x100"
    assert first_small["properties"]["big_number"] == 1
    assert first_small["properties"]["big_name"] == "Северный участок"
    assert first_small["properties"]["small_number"] == 1


def test_write_csv_all_uses_bom_semicolon_and_cell_rows(tmp_path: Path) -> None:
    out_path = tmp_path / "grid.csv"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        big_tile_names=((1, "Северный участок"),),
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.CSV,
    )

    write_csv_all(out_path, _bounds_2x2_big(), options)
    raw = out_path.read_bytes()
    text = raw.decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))

    assert raw.startswith(b"\xef\xbb\xbf")
    assert text.splitlines()[0] == ";".join(CSV_HEADER)
    assert len(rows) == 404
    assert rows[0]["layer"] == "1000x1000"
    assert rows[0]["zone"] == "6"
    assert rows[0]["big_number"] == "1"
    assert rows[0]["big_name"] == "Северный участок"
    assert rows[0]["small_number"] == ""
    assert rows[0]["x_top"] == "5662000"
    assert rows[0]["x_bottom"] == "5661000"
    assert rows[0]["y_left"] == "6650000"
    assert rows[0]["y_right"] == "6651000"
    assert rows[0]["center_lon"]
    assert rows[0]["center_lat"]
    assert rows[1]["layer"] == "100x100"
    assert rows[1]["big_number"] == "1"
    assert rows[1]["big_name"] == "Северный участок"
    assert rows[1]["small_number"] == "1"


def test_svg_style_uses_kml_style_colors_and_opacity(tmp_path: Path) -> None:
    out_path = tmp_path / "styled.svg"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.SVG,
        kml_style=KmlStyle(
            big_line_color="#ff0000",
            small_line_color="#00ff00",
            big_line_width=5,
            small_line_width=3,
            big_fill_mode=BigTileFillMode.SINGLE,
            big_fill_color="#3366cc",
            big_fill_opacity=50,
            small_fill_enabled=True,
            small_fill_color="#112233",
            small_fill_opacity=40,
        ),
    )

    write_svg_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)
    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    svg_ns = "{http://www.w3.org/2000/svg}"
    rects = root.findall(f".//{svg_ns}rect")
    big_rect = next(rect for rect in rects if rect.attrib["data-layer"] == "1000x1000")
    small_rects = [rect for rect in rects if rect.attrib["data-layer"] == "100x100"]

    assert big_rect.attrib["stroke"] == "#ff0000"
    assert big_rect.attrib["stroke-width"] == "5"
    assert big_rect.attrib["fill"] == "#3366cc"
    assert big_rect.attrib["fill-opacity"] == "0.5"
    assert len(small_rects) == 100
    assert all(rect.attrib["stroke"] == "#00ff00" for rect in small_rects)
    assert all(rect.attrib["stroke-width"] == "3" for rect in small_rects)
    assert all(rect.attrib["fill"] == "#112233" for rect in small_rects)
    assert all(rect.attrib["fill-opacity"] == "0.4" for rect in small_rects)


def test_custom_line_style_is_written_to_big_and_small_tiles(tmp_path: Path) -> None:
    out_path = tmp_path / "styled-lines.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
        kml_style=KmlStyle(
            big_line_color="#ff0000",
            small_line_color="#00ff00",
            big_line_width=5,
            small_line_width=3,
        ),
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)
    text = out_path.read_text(encoding="utf-8")

    assert "<color>ff0000ff</color>" in text
    assert "<width>5</width>" in text
    assert text.count("<color>ff00ff00</color>") == 100
    assert text.count("<width>3</width>") == 100
    assert text.count("<fill>0</fill>") == 101


def test_big_fill_uses_alpha_and_small_tiles_stay_without_fill(tmp_path: Path) -> None:
    out_path = tmp_path / "big-fill.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
        kml_style=KmlStyle(
            big_fill_mode=BigTileFillMode.SINGLE,
            big_fill_color="#3366cc",
            big_fill_opacity=50,
        ),
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)
    text = out_path.read_text(encoding="utf-8")

    assert "<color>80cc6633</color>" in text
    assert text.count("<fill>1</fill>") == 1
    assert text.count("<fill>0</fill>") == 100


def test_small_fill_is_written_to_each_small_tile(tmp_path: Path) -> None:
    out_path = tmp_path / "small-fill.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
        kml_style=KmlStyle(
            small_fill_enabled=True,
            small_fill_color="#112233",
            small_fill_opacity=40,
        ),
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)
    text = out_path.read_text(encoding="utf-8")
    root = ElementTree.fromstring(text)

    placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert len(placemarks) == 101
    assert "Заливка 100x100" not in text
    assert text.count("<color>66332211</color>") == 100
    assert text.count("<fill>1</fill>") == 100
    assert text.count("<fill>0</fill>") == 1
    assert "<outline>0</outline>" not in text


def test_custom_palette_applies_only_to_big_tiles(tmp_path: Path) -> None:
    out_path = tmp_path / "palette.kml"
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
        kml_style=KmlStyle(
            big_fill_mode=BigTileFillMode.CUSTOM,
            big_fill_color="#abcdef",
            big_fill_opacity=100,
            custom_big_fill_colors=((2, "#123456"),),
        ),
    )

    write_kml_all(out_path, _bounds_2x2_big(), options)
    text = out_path.read_text(encoding="utf-8")

    assert "<color>ffefcdab</color>" in text
    assert "<color>ff563412</color>" in text
    assert text.count("<fill>1</fill>") == 4


def test_number_palette_cycles_by_big_tile_number(tmp_path: Path) -> None:
    out_path = tmp_path / "number-palette.kml"
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
        kml_style=KmlStyle(
            big_fill_mode=BigTileFillMode.BY_NUMBER,
            big_fill_opacity=100,
            big_fill_palette=("#ff0000", "#00ff00"),
        ),
    )

    write_kml_all(out_path, _bounds_2x2_big(), options)
    text = out_path.read_text(encoding="utf-8")

    assert text.count("<color>ff0000ff</color>") == 2
    assert text.count("<color>ff00ff00</color>") == 2
    assert text.count("<fill>1</fill>") == 4


def test_zip_contains_one_kml_per_big_tile(tmp_path: Path) -> None:
    out_path = tmp_path / "tiles.zip"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.ZIP,
    )

    write_zip_per_big_tile(out_path, _bounds_2x2_big(), options)

    with zipfile.ZipFile(out_path) as zf:
        assert sorted(zf.namelist()) == ["tile_001.kml", "tile_002.kml", "tile_003.kml", "tile_004.kml"]
        tile = zf.read("tile_001.kml").decode("utf-8")

    root = ElementTree.fromstring(tile)
    document_name = root.find(".//{http://www.opengis.net/kml/2.2}Document/{http://www.opengis.net/kml/2.2}name")
    placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert document_name is not None
    assert document_name.text == "Квадрат 001"
    assert len(placemarks) == 101


def test_export_progress_counts_big_and_small_placemarks(tmp_path: Path) -> None:
    out_path = tmp_path / "progress.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    progress: list[tuple[int, int]] = []

    write_kml_all(out_path, _bounds_2x2_big(), options, progress=lambda done, total: progress.append((done, total)))

    assert progress[0] == (0, 404)
    assert progress[-1] == (404, 404)


def test_export_cancel_removes_temporary_file(tmp_path: Path) -> None:
    out_path = tmp_path / "cancel.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    cancel_requested = False

    def progress(done: int, _total: int) -> None:
        nonlocal cancel_requested
        if done > 0:
            cancel_requested = True

    with pytest.raises(ExportCancelled):
        export_grid(out_path, _bounds_2x2_big(), options, progress=progress, cancelled=lambda: cancel_requested)

    assert not out_path.exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_export_grid_writes_svg_through_temporary_file(tmp_path: Path) -> None:
    out_path = tmp_path / "result.svg"
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.SVG,
    )

    export_grid(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    assert out_path.exists()
    assert ElementTree.fromstring(out_path.read_text(encoding="utf-8")).tag == "{http://www.w3.org/2000/svg}svg"
    assert not list(tmp_path.glob("*.tmp"))


def test_export_grid_writes_geojson_and_csv_through_temporary_file(tmp_path: Path) -> None:
    bounds = Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000)
    geojson_path = tmp_path / "result.geojson"
    csv_path = tmp_path / "result.csv"

    export_grid(
        geojson_path,
        bounds,
        GridOptions(include_1000=True, include_100=False, rounding_mode=RoundingMode.NONE, export_mode=ExportMode.GEOJSON),
    )
    export_grid(
        csv_path,
        bounds,
        GridOptions(include_1000=True, include_100=False, rounding_mode=RoundingMode.NONE, export_mode=ExportMode.CSV),
    )

    assert json.loads(geojson_path.read_text(encoding="utf-8"))["type"] == "FeatureCollection"
    assert csv_path.read_bytes().startswith(b"\xef\xbb\xbf")
    assert not list(tmp_path.glob("*.tmp"))


def test_zip_tile_keeps_custom_kml_style(tmp_path: Path) -> None:
    out_path = tmp_path / "styled.zip"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.ZIP,
        kml_style=KmlStyle(
            big_line_color="#ff0000",
            small_line_color="#00ff00",
            big_fill_mode=BigTileFillMode.SINGLE,
            big_fill_color="#3366cc",
            big_fill_opacity=50,
            small_fill_enabled=True,
            small_fill_color="#112233",
            small_fill_opacity=40,
        ),
    )

    write_zip_per_big_tile(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    with zipfile.ZipFile(out_path) as zf:
        tile = zf.read("tile_001.kml").decode("utf-8")

    assert "<color>ff0000ff</color>" in tile
    assert "<color>80cc6633</color>" in tile
    assert tile.count("<color>66332211</color>") == 100
    assert tile.count("<color>ff00ff00</color>") == 100
    assert tile.count("<fill>1</fill>") == 101
    assert "<fill>0</fill>" not in tile
    assert "<outline>0</outline>" not in tile


def test_export_uses_custom_small_numbering(tmp_path: Path) -> None:
    out_path = tmp_path / "custom.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        small_numbering_mode=SmallNumberingMode.LINEAR,
        small_numbering_direction=SmallNumberingDirection.BY_ROWS,
        small_numbering_start_corner=StartCorner.NE,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    placemark_names = [
        node.text
        for node in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark/{http://www.opengis.net/kml/2.2}name")
    ]
    assert placemark_names[0] == "001"
    assert placemark_names[1:11] == ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1"]


def test_export_uses_spiral_small_numbering(tmp_path: Path) -> None:
    out_path = tmp_path / "spiral.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        small_numbering_mode=SmallNumberingMode.SPIRAL_CENTER_OUT,
        small_numbering_direction=SmallNumberingDirection.BY_ROWS,
        small_numbering_start_corner=StartCorner.NW,
        small_spiral_direction=SpiralDirection.CLOCKWISE,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    placemark_names = [
        node.text
        for node in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark/{http://www.opengis.net/kml/2.2}name")
    ]
    assert placemark_names[0] == "001"
    assert placemark_names[1:11] == ["73", "74", "75", "76", "77", "78", "79", "80", "81", "82"]


def test_export_uses_custom_big_tile_name_without_changing_small_numbers(tmp_path: Path) -> None:
    out_path = tmp_path / "renamed.kml"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=True,
        big_tile_names=((1, "Северный участок & A"),),
        small_numbering_mode=SmallNumberingMode.LINEAR,
        small_numbering_direction=SmallNumberingDirection.BY_ROWS,
        small_numbering_start_corner=StartCorner.NE,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )

    write_kml_all(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    folder_names = [
        node.text
        for node in root.findall(".//{http://www.opengis.net/kml/2.2}Folder/{http://www.opengis.net/kml/2.2}name")
    ]
    placemark_names = [
        node.text
        for node in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark/{http://www.opengis.net/kml/2.2}name")
    ]
    assert folder_names[0] == "Северный участок & A"
    assert placemark_names[0] == "Северный участок & A"
    assert placemark_names[1:11] == ["10", "9", "8", "7", "6", "5", "4", "3", "2", "1"]


def test_zip_keeps_standard_filename_with_custom_big_tile_name(tmp_path: Path) -> None:
    out_path = tmp_path / "renamed.zip"
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=True,
        big_tile_names=((1, "Северный участок"),),
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.ZIP,
    )

    write_zip_per_big_tile(out_path, Bounds(5_661_000, 5_660_000, 6_650_000, 6_651_000), options)

    with zipfile.ZipFile(out_path) as zf:
        assert zf.namelist() == ["tile_001.kml"]
        tile = zf.read("tile_001.kml").decode("utf-8")

    root = ElementTree.fromstring(tile)
    document_name = root.find(".//{http://www.opengis.net/kml/2.2}Document/{http://www.opengis.net/kml/2.2}name")
    placemark_names = [
        node.text
        for node in root.findall(".//{http://www.opengis.net/kml/2.2}Placemark/{http://www.opengis.net/kml/2.2}name")
    ]
    assert document_name is not None
    assert document_name.text == "Северный участок"
    assert placemark_names == ["Северный участок"]


def test_multizone_kml_uses_transformer_for_each_big_tile(tmp_path: Path) -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )

    out_path = tmp_path / "multizone.kml"
    write_kml_all(out_path, _bounds_2x2_big_crossing_zones(), options)
    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    coordinates = [
        placemark.find(".//{http://www.opengis.net/kml/2.2}coordinates").text
        for placemark in placemarks
    ]
    first_lon, first_lat, _ = coordinates[0].split()[0].split(",")
    second_lon, second_lat, _ = coordinates[1].split()[0].split(",")
    expected_zone_6 = ck42_to_wgs84(5_662_000, 6_999_000, make_transformer_for_zone(6))
    expected_zone_7 = ck42_to_wgs84(5_662_000, 7_000_000, make_transformer_for_zone(7))

    assert len(placemarks) == 4
    assert (float(first_lon), float(first_lat)) == pytest.approx(expected_zone_6, abs=1e-7)
    assert (float(second_lon), float(second_lat)) == pytest.approx(expected_zone_7, abs=1e-7)


def test_multizone_geojson_csv_svg_and_zip_keep_global_cells(tmp_path: Path) -> None:
    bounds = _bounds_2x2_big_crossing_zones()
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=False,
        rounding_mode=RoundingMode.NONE,
    )

    geojson_path = tmp_path / "multizone.geojson"
    csv_path = tmp_path / "multizone.csv"
    svg_path = tmp_path / "multizone.svg"
    zip_path = tmp_path / "multizone.zip"
    write_geojson_all(geojson_path, bounds, GridOptions(**{**options.__dict__, "export_mode": ExportMode.GEOJSON}))
    write_csv_all(csv_path, bounds, GridOptions(**{**options.__dict__, "export_mode": ExportMode.CSV}))
    write_svg_all(svg_path, bounds, GridOptions(**{**options.__dict__, "export_mode": ExportMode.SVG}))
    write_zip_per_big_tile(zip_path, bounds, GridOptions(**{**options.__dict__, "export_mode": ExportMode.ZIP}))

    features = json.loads(geojson_path.read_text(encoding="utf-8"))["features"]
    csv_rows = list(csv.DictReader(io.StringIO(csv_path.read_bytes().decode("utf-8-sig")), delimiter=";"))
    svg_root = ElementTree.fromstring(svg_path.read_text(encoding="utf-8"))
    svg_ns = "{http://www.w3.org/2000/svg}"
    rects = svg_root.findall(f".//{svg_ns}rect")

    assert [feature["properties"]["zone"] for feature in features] == [6, 7, 6, 7]
    assert [feature["properties"]["big_number"] for feature in features] == [1, 2, 3, 4]
    assert [row["zone"] for row in csv_rows] == ["6", "7", "6", "7"]
    assert [row["big_number"] for row in csv_rows] == ["1", "2", "3", "4"]
    assert svg_root.attrib["data-zone"] == "6,7"
    assert {rect.attrib["data-zone"] for rect in rects} == {"6", "7"}
    with zipfile.ZipFile(zip_path) as zf:
        assert sorted(zf.namelist()) == ["tile_001.kml", "tile_002.kml", "tile_003.kml", "tile_004.kml"]


def test_multizone_geojson_keeps_small_numbers_local_inside_big_tiles(tmp_path: Path) -> None:
    out_path = tmp_path / "multizone-small.geojson"
    options = GridOptions(
        include_1000=True,
        include_100=True,
        snake_big=False,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.GEOJSON,
    )
    bounds = Bounds(x_top=5_661_000, x_bottom=5_660_000, y_left=6_999_000, y_right=7_001_000)

    write_geojson_all(out_path, bounds, options)
    features = json.loads(out_path.read_text(encoding="utf-8"))["features"]

    assert len(features) == 202
    assert features[0]["properties"]["layer"] == "1000x1000"
    assert features[0]["properties"]["zone"] == 6
    assert features[1]["properties"]["small_number"] == 1
    assert features[1]["properties"]["zone"] == 6
    assert features[101]["properties"]["layer"] == "1000x1000"
    assert features[101]["properties"]["zone"] == 7
    assert features[102]["properties"]["small_number"] == 1
    assert features[102]["properties"]["zone"] == 7


def test_cell_crossing_zone_boundary_raises(tmp_path: Path) -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_500, y_right=7_001_500)

    with pytest.raises(ValueError, match="внутри одной ячейки"):
        write_kml_all(tmp_path / "bad.kml", bounds, options)
