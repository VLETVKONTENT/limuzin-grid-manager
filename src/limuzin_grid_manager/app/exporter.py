from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil
import tempfile

from limuzin_grid_manager.core.kml import ExportCancelled, write_kml_all, write_zip_per_big_tile
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions, GridStats
from limuzin_grid_manager.core.stats import ensure_exportable, estimate_export_size_bytes


def export_grid(
    out_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> None:
    options = options.normalized()
    stats = ensure_exportable(bounds, options)
    check_free_space_for_export(out_path, stats, options)

    temp_path = _temporary_output_path(out_path)
    try:
        if options.export_mode == ExportMode.ZIP:
            write_zip_per_big_tile(temp_path, bounds, options, progress=progress, cancelled=cancelled)
        else:
            write_kml_all(temp_path, bounds, options, progress=progress, cancelled=cancelled)
        if cancelled is not None and cancelled():
            raise ExportCancelled("Экспорт отменен пользователем.")
        temp_path.replace(out_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def check_free_space_for_export(out_path: Path, stats: GridStats, options: GridOptions) -> None:
    required = estimate_export_size_bytes(stats, options)
    if required <= 0:
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(out_path.parent).free
    if free < required:
        raise OSError(
            "Недостаточно свободного места для экспорта. "
            f"Нужно примерно {_format_bytes(required)}, доступно {_format_bytes(free)}. "
            "Выберите другую папку или уменьшите область."
        )


def parse_meter(value: str, label: str = "Координата") -> int:
    cleaned = "".join(value.split()).replace(",", ".")
    if not cleaned:
        raise ValueError(f"{label} не заполнена.")
    try:
        return int(float(cleaned))
    except ValueError as exc:
        raise ValueError(
            f"{label} должна быть числом в метрах. Можно вводить 5660000, 5 660 000 или 5660000,0."
        ) from exc


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
