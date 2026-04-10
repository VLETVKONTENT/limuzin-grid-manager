from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
import shutil
import tempfile

from limuzin_grid_manager.core.export_progress import ExportCancelled
from limuzin_grid_manager.core.point_kml import write_points_kml
from limuzin_grid_manager.core.points import PointRecord, PointStyle

POINT_KML_BYTES_PER_PLACEMARK = 600
POINT_EXPORT_SIZE_SAFETY_BYTES = 1_048_576


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
    check_free_space_for_points_export(out_path, point_records)

    temp_path = _temporary_output_path(out_path)
    try:
        write_points_kml(
            temp_path,
            point_records,
            style.normalized(),
            progress=progress,
            cancelled=cancelled,
        )
        if cancelled is not None and cancelled():
            raise ExportCancelled("Экспорт отменен пользователем.")
        temp_path.replace(out_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def check_free_space_for_points_export(out_path: Path, records: Sequence[PointRecord]) -> None:
    required = estimate_points_export_size_bytes(records)
    if required <= 0:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(out_path.parent).free
    if free < required:
        raise OSError(
            "Недостаточно свободного места для point-KML. "
            f"Нужно примерно {_format_bytes(required)}, доступно {_format_bytes(free)}. "
            "Выберите другую папку или уменьшите набор точек."
        )


def estimate_points_export_size_bytes(records: Sequence[PointRecord]) -> int:
    point_records = tuple(records)
    if not point_records:
        return 0
    return POINT_EXPORT_SIZE_SAFETY_BYTES + len(point_records) * POINT_KML_BYTES_PER_PLACEMARK


def _temporary_output_path(out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        delete=False,
        dir=out_path.parent,
        prefix=f".{out_path.name}.",
        suffix=".tmp",
    ) as temp_file:
        return Path(temp_file.name)


def _format_bytes(value: int) -> str:
    units = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    size = float(max(0, value))
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == "Б":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{int(size)} Б"
