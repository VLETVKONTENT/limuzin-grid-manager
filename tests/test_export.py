from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree

import pytest

from limuzin_grid_manager.core.kml import write_kml_all, write_zip_per_big_tile
from limuzin_grid_manager.core.models import (
    Bounds,
    ExportMode,
    GridOptions,
    RoundingMode,
    SmallNumberingDirection,
    SmallNumberingMode,
    SpiralDirection,
    StartCorner,
)


def _bounds_2x2_big() -> Bounds:
    return Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_650_000, y_right=6_652_000)


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
    placemarks = root.findall(".//{http://www.opengis.net/kml/2.2}Placemark")
    assert len(placemarks) == 101


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


def test_zone_crossing_raises(tmp_path: Path) -> None:
    options = GridOptions(
        include_1000=True,
        include_100=False,
        snake_big=True,
        rounding_mode=RoundingMode.NONE,
        export_mode=ExportMode.KML,
    )
    bounds = Bounds(x_top=5_662_000, x_bottom=5_660_000, y_left=6_999_000, y_right=7_001_000)

    with pytest.raises(ValueError, match="границу зон"):
        write_kml_all(tmp_path / "bad.kml", bounds, options)
