# GRIDBASE: LIMUZIN GRID MANAGER

This file is the compact technical base for the project. It is meant to be a reliable working reference for future coding sessions and maintenance.

Current stable version: `v2.2.0`

## Purpose

LIMUZIN GRID MANAGER is a Windows desktop application for:

- generating `1000x1000` and `100x100` grids for AlpineQuest
- exporting those grids to `KML`, `ZIP`, `SVG`, `GeoJSON`, and `CSV`
- importing points from Excel and exporting them as point `KML`

The application is built around SK-42 / Pulkovo-42, Gauss-Kruger coordinates and converts them to WGS84 for export.

## Stack

- Python `>=3.11,<3.15`
- PySide6
- `pyproj`
- `openpyxl`
- `uv`
- `pytest`
- PyInstaller for Windows EXE

## Repository layout

- `src/limuzin_grid_manager/app/` - application services
- `src/limuzin_grid_manager/core/` - geometry, CRS, export logic, models, numbering, validation
- `src/limuzin_grid_manager/ui/` - PySide6 windows, preview, themes
- `tests/` - automated tests
- `versions/` - version notes and archived plans
- `versions/roadmaps_archive/` - historical roadmaps and completed execution plans

## Main modules

- `src/limuzin_grid_manager/__main__.py` - GUI entry point
- `src/limuzin_grid_manager/core/crs.py` - SK-42 to WGS84 transformation
- `src/limuzin_grid_manager/core/zones.py` - Gauss-Kruger zones and zone splitting
- `src/limuzin_grid_manager/core/geometry.py` - bounds normalization, rounding, grid math
- `src/limuzin_grid_manager/core/numbering.py` - numbering modes for `100x100`
- `src/limuzin_grid_manager/core/kml.py` - KML and ZIP writing
- `src/limuzin_grid_manager/core/svg.py` - SVG export
- `src/limuzin_grid_manager/core/geojson.py` - GeoJSON export
- `src/limuzin_grid_manager/core/csv_export.py` - CSV export
- `src/limuzin_grid_manager/core/points.py` - point domain models and normalization
- `src/limuzin_grid_manager/core/point_kml.py` - point KML writer
- `src/limuzin_grid_manager/core/stats.py` - validation, warnings, exportability checks
- `src/limuzin_grid_manager/app/exporter.py` - grid export orchestration and atomic writing
- `src/limuzin_grid_manager/app/project.py` - `.lgm.json` save/load
- `src/limuzin_grid_manager/app/point_import.py` - Excel import
- `src/limuzin_grid_manager/app/point_exporter.py` - point KML export orchestration
- `src/limuzin_grid_manager/app/runtime.py` - runtime logging
- `src/limuzin_grid_manager/ui/main_window.py` - main grid window
- `src/limuzin_grid_manager/ui/points_window.py` - separate points window
- `src/limuzin_grid_manager/ui/preview.py` - 2D preview
- `src/limuzin_grid_manager/ui/themes.py` - UI themes

## Non-negotiable behavior

### Coordinates

- input is `X/Y`
- `pyproj` receives `Y/X`
- KML and GeoJSON store `lon,lat`
- zone formula is `int(abs(Y) // 1_000_000)`
- supported zone range is `1..32`

### Zones

Multi-zone export is supported only when each exported cell lies fully inside one zone.

That means:

- an area may span several zones
- exports may be split logically by zone
- a single `1000x1000` or `100x100` cell must not cross a zone boundary inside itself
- if a cell crosses a zone boundary inside itself, export must fail with a clear error

### Grids and numbering

- the grid is built top-to-bottom and left-to-right
- numbering for `100x100` supports linear, snake, and spiral variants
- renaming `1000x1000` tiles must not renumber inner `100x100` tiles

### Export behavior

- default KML style stays black with fill disabled
- ZIP export is available only with `1000x1000`
- ZIP entry names stay `tile_###.kml`
- large exports use streaming where appropriate, progress, cancellation, free-space checks, and atomic writing

### Projects

- `.lgm.json` loading is strict
- boolean fields must be real JSON booleans
- corrupted lists and malformed project data must raise user-friendly errors
- the last project path is stored in local `QSettings`, not in the repo and not inside `.lgm.json`

### Points workflow

- point workflow remains separate from grid workflow
- it must not extend `GridOptions`, grid export modes, or `.lgm.json` unless that becomes a separate explicit task
- Excel import and point export run in background workers

## Architecture rules

- do not mix UI code with coordinate math
- put geometry, CRS, numbering, and export logic in `core`
- keep orchestration and file management in `app`
- keep widgets, dialogs, and thread wiring in `ui`
- new export formats should be added through separate modules or services, not by growing `MainWindow`
- do not reintroduce Tkinter from the old prototype

## Validation commands

Run after normal code changes:

```powershell
uv run --extra dev pytest
uv run --extra dev python -m compileall src tests
```

Run before handing a release candidate to a user:

```powershell
uv lock --offline
uv run --offline --extra dev pytest
uv run --offline --extra dev python -m compileall src tests
$env:UV_OFFLINE='1'; .\build_exe_windows.bat
```

## Documentation map

- `README.md` - repository overview and quick start
- `USER_GUIDE.md` - user-facing workflow
- `GITHUB.md` - git, CI, release, and publication rules
- `versions/GRIDVERSIONS.md` - version index
- `versions/vX.Y.Z.md` - release notes
- `versions/roadmaps_archive/roadmap.md` - archived roadmap up to `v1.0`
- `versions/roadmaps_archive/ROADMAPv2.md` - archived roadmap for `v1.0 -> v2.0`
- `versions/roadmaps_archive/ROADMAPv2.1.md` - archived roadmap for `v2.0 -> v2.1`
- `versions/roadmaps_archive/FIXPROD.md` - archived hardening plan up to `v2.2.0`

If code and docs disagree, trust the current code and tests first, then update the documentation together with the behavior change.
