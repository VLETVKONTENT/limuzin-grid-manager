from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from limuzin_grid_manager.core.kml import write_kml_all, write_zip_per_big_tile
from limuzin_grid_manager.core.models import Bounds, ExportMode, GridOptions


def export_grid(
    out_path: Path,
    bounds: Bounds,
    options: GridOptions,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    options = options.normalized()
    if options.export_mode == ExportMode.ZIP:
        write_zip_per_big_tile(out_path, bounds, options, progress=progress)
    else:
        write_kml_all(out_path, bounds, options, progress=progress)


def parse_meter(value: str) -> int:
    cleaned = "".join(value.split()).replace(",", ".")
    if not cleaned:
        raise ValueError("Координата не заполнена.")
    return int(float(cleaned))
