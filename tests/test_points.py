from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from xml.etree import ElementTree

import pytest

from limuzin_grid_manager.app.point_exporter import export_points_kml
from limuzin_grid_manager.app.point_import import PointImportError, PointImportResult
from limuzin_grid_manager.core.point_kml import write_points_kml
from limuzin_grid_manager.core.points import (
    PointRecord,
    PointStyle,
    normalize_point_date,
    parse_point_coordinates,
    point_style_to_kml_color,
)


def _sample_record(
    *,
    name: str = "Мишарин Александр Витальевич",
    source_date: str = "46115",
    display_date: object = "03.04.2026",
    x: int = -5_649_764,
    y: int = -6_661_612,
    zone: int = 6,
    lon: float = 35.29845459878114,
    lat: float = 50.955512683199146,
    source_row: int = 2,
) -> PointRecord:
    return PointRecord(
        name=name,
        source_date=source_date,
        display_date=display_date,
        x=x,
        y=y,
        zone=zone,
        lon=lon,
        lat=lat,
        source_row=source_row,
    )


def test_point_record_validates_and_normalizes_fields() -> None:
    record = _sample_record(name="  Точка  ", display_date=46115)

    assert record.name == "Точка"
    assert record.source_date == "46115"
    assert record.display_date == "03.04.2026"
    assert record.zone == 6
    assert record.source_row == 2

    with pytest.raises(ValueError, match="зона"):
        _sample_record(zone=33)


def test_point_style_and_helpers_normalize_color_opacity_and_date() -> None:
    style = PointStyle(color="123456", opacity=50).normalized()

    assert style == PointStyle(color="#123456", opacity=50)
    assert point_style_to_kml_color(style) == "80563412"
    assert normalize_point_date("46115") == "03.04.2026"
    assert normalize_point_date(date(2026, 4, 3)) == "03.04.2026"
    assert normalize_point_date(datetime(2026, 4, 3, 15, 45)) == "03.04.2026"


def test_parse_point_coordinates_extracts_two_integers() -> None:
    assert parse_point_coordinates("х-5649764 y-6661612") == (-5_649_764, -6_661_612)
    assert parse_point_coordinates("x=5649800, y=6661934") == (5_649_800, 6_661_934)

    with pytest.raises(ValueError, match="ровно два"):
        parse_point_coordinates("x=12 y=34 z=56")

    with pytest.raises(ValueError, match="целыми числами"):
        parse_point_coordinates("x=12.5 y=34")


def test_point_import_result_summary_blocks_export_on_errors() -> None:
    result = PointImportResult(
        sheet_name="Лист1",
        records=(_sample_record(),),
        errors=(PointImportError(source_row=3, message="Пустая дата."),),
        total_rows=2,
    )

    assert not result.is_exportable
    assert "Лист: Лист1" in result.summary
    assert "Корректных точек: 1." in result.summary
    assert "Ошибок: 1. Экспорт заблокирован." in result.summary


def test_write_points_kml_creates_waypoints_document_with_point_placemarks(tmp_path: Path) -> None:
    out_path = tmp_path / "points.kml"
    records = (
        _sample_record(),
        _sample_record(
            name="Педьков Михаил Иванович",
            x=-5_649_800,
            y=-6_661_934,
            lon=35.29800696743792,
            lat=50.95487717694347,
            source_row=3,
        ),
    )

    write_points_kml(out_path, records, PointStyle(color="#123456", opacity=50))
    root = ElementTree.fromstring(out_path.read_text(encoding="utf-8"))
    ns = "{http://www.opengis.net/kml/2.2}"

    document_name = root.find(f"./{ns}Document/{ns}name")
    placemarks = root.findall(f".//{ns}Placemark")
    first = placemarks[0]

    assert document_name is not None
    assert document_name.text == "Waypoints"
    assert len(placemarks) == 2
    assert first.find(f"./{ns}name").text == "Мишарин Александр Витальевич"
    assert first.find(f"./{ns}description").text == "<i>03.04.2026</i>"
    assert first.find(f"./{ns}ExtendedData/{ns}Data").text == "03.04.2026"
    assert first.find(f"./{ns}Style/{ns}IconStyle/{ns}color").text == "80563412"

    coords_text = first.find(f"./{ns}Point/{ns}coordinates").text
    lon_text, lat_text = coords_text.split(",")
    assert float(lon_text) == pytest.approx(35.29845459878114, abs=1e-14)
    assert float(lat_text) == pytest.approx(50.955512683199146, abs=1e-14)


def test_write_points_kml_reports_progress() -> None:
    progress: list[tuple[int, int]] = []

    write_points_kml(
        Path("NUL"),
        (_sample_record(), _sample_record(source_row=3, name="Педьков Михаил Иванович")),
        PointStyle(),
        progress=lambda done, total: progress.append((done, total)),
    )

    assert progress[0] == (0, 2)
    assert progress[-1] == (2, 2)


def test_export_points_kml_requires_records_and_writes_output(tmp_path: Path) -> None:
    out_path = tmp_path / "exported_points.kml"

    with pytest.raises(ValueError, match="Нет точек"):
        export_points_kml(out_path, (), PointStyle())

    export_points_kml(out_path, (_sample_record(),), PointStyle(color="#123456", opacity=50))

    assert out_path.exists()
    assert ElementTree.fromstring(out_path.read_text(encoding="utf-8")).tag == "{http://www.opengis.net/kml/2.2}kml"
