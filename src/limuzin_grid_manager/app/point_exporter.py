from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from limuzin_grid_manager.core.point_kml import write_points_kml
from limuzin_grid_manager.core.points import PointRecord, PointStyle


def export_points_kml(
    out_path: Path,
    records: Sequence[PointRecord],
    style: PointStyle,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    point_records = tuple(records)
    if not point_records:
        raise ValueError("Нет точек для экспорта в KML.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_points_kml(out_path, point_records, style.normalized(), progress=progress, cancelled=cancelled)
