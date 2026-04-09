from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO
from xml.sax.saxutils import escape

from limuzin_grid_manager.core.export_progress import ProgressTracker
from limuzin_grid_manager.core.points import PointRecord, PointStyle, point_style_to_kml_color


def write_points_kml(
    out_path: Path,
    records: Sequence[PointRecord],
    style: PointStyle,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    point_records = tuple(records)
    tracker = ProgressTracker(progress, len(point_records), cancelled)
    kml_color = point_style_to_kml_color(style)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="\n") as fh:
        _write_document_start(fh)
        for record in point_records:
            _write_point_placemark(fh, record, kml_color)
            tracker.step()
        _write_document_end(fh)
    tracker.finish()


def _write_document_start(fh: TextIO) -> None:
    fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    fh.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    fh.write("<Document>\n")
    fh.write("<name>Waypoints</name>\n")
    fh.write("<open>1</open>\n")


def _write_document_end(fh: TextIO) -> None:
    fh.write("</Document></kml>\n")


def _write_point_placemark(fh: TextIO, record: PointRecord, kml_color: str) -> None:
    fh.write("<Placemark>\n")
    fh.write(f"<name>{escape(record.name)}</name>\n")
    fh.write(f"<description><![CDATA[<i>{record.display_date}</i>]]></description>\n")
    fh.write("<ExtendedData>\n")
    fh.write(f'<Data name="comment"><![CDATA[{record.display_date}]]></Data>\n')
    fh.write("</ExtendedData>\n")
    fh.write("<Style>\n")
    fh.write("<IconStyle>\n")
    fh.write(f"<color>{kml_color}</color>\n")
    fh.write("</IconStyle>\n")
    fh.write("</Style>\n")
    fh.write("<Point>\n")
    fh.write(f"<coordinates>{_format_coord(record.lon)},{_format_coord(record.lat)}</coordinates>\n")
    fh.write("</Point>\n")
    fh.write("</Placemark>\n")


def _format_coord(value: float) -> str:
    text = f"{value:.14f}".rstrip("0").rstrip(".")
    if "." not in text:
        return f"{text}.0"
    return text
