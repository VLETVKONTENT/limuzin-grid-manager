# LIMUZIN GRID MANAGER

LIMUZIN GRID MANAGER is a Windows desktop application for preparing grid exports and point KML files for AlpineQuest.

Current version: `v2.2.0`

Stable accepted version: `v2.2.0`

Previous stable version: `v2.1.4`

## What the app does

The application works with SK-42 / Pulkovo-42 Gauss-Kruger coordinates in meters and supports two main workflows:

- Grid workflow: build `1000x1000` and `100x100` grids, preview them, validate the area, and export the result.
- Points from Excel workflow: import points from a sample-first `.xlsx` file and generate a point KML file.

Supported grid export formats:

- `KML` as one common file
- `ZIP` with `tile_###.kml` files for `1000x1000` tiles
- `SVG`
- `GeoJSON`
- `CSV`

Supported point export:

- point `KML` from the separate `Points from Excel` window

## Key features

- PySide6 desktop UI for Windows
- grids `1000x1000` and `100x100`
- several numbering modes for `100x100`, including linear, snake, and spiral
- custom names for big `1000x1000` tiles without renumbering small tiles
- configurable KML styling, including fill modes for `1000x1000` and common fill for `100x100`
- 2D preview with zoom, pan, simplified rendering for large areas, and validation summary
- zone-aware export for areas spanning multiple Gauss-Kruger zones
- protection against cells that cross a zone boundary inside a single tile
- atomic export through a temporary file, progress reporting, free-space checks, and cancellation
- strict `.lgm.json` project loading and atomic project saving
- separate Excel import window with background import/export and runtime logging
- Windows EXE build via PyInstaller

## Quick start

### Run from source

Requirements:

- Windows
- Python `>=3.11,<3.15`
- `uv`

Install dependencies:

```powershell
uv sync --extra dev
```

Run the app:

```powershell
uv run limuzin-grid-manager
```

### Build EXE

```powershell
.\build_exe_windows.bat
```

Result:

```text
dist/LIMUZIN_GRID_MANAGER.exe
```

By default the EXE is unsigned. The build script also supports optional local Authenticode signing through `LGM_SIGN_*` environment variables.

## How to use

### Grid workflow

1. Enter two points of the area in SK-42 / Gauss-Kruger coordinates:
   `NW X`, `NW Y`, `SE X`, `SE Y`
2. Choose which grid layers to build:
   `1000x1000`, `100x100`, or both
3. Set rounding mode, numbering, names, and KML style if needed
4. Check the preview and the validation tab
5. Choose export format and output path
6. Generate the result

### Points from Excel

Open `Tools -> Points from Excel...`

The Excel workflow expects a sample-first `.xlsx` file with columns:

```text
ФИО | Дата | Координаты
```

Coordinates are parsed from one text cell, converted from SK-42 to WGS84, and exported as point placemarks in KML.

## Coordinates and zones

- Input format: SK-42 / Pulkovo-42, Gauss-Kruger, meters
- Input order: user enters `X/Y`
- `pyproj` receives `Y/X`
- KML and GeoJSON store coordinates as `lon,lat`
- Zone formula: `zone = int(abs(Y) // 1_000_000)`
- Supported zones: `1..32`

Multi-zone areas are supported, but only if each exported cell stays fully inside one zone. If a `1000x1000` or `100x100` cell crosses a zone boundary inside the cell, export is blocked with a clear error.

## Project files and logs

### Project file

The application can save and reopen working state in `.lgm.json`.

Project file includes:

- bounds
- grid options
- numbering options
- tile names
- KML style
- export settings

The last opened or saved project path is stored locally through `QSettings`, not inside the repository and not inside the project file itself.

### Runtime log

Unexpected runtime failures are written to:

```text
%LOCALAPPDATA%\LIMUZIN GRID MANAGER\logs\runtime.log
```

If the default app-data directory is unavailable, the application uses a writable fallback directory inside the user profile.

## Development

### Tests

Run the full test suite:

```powershell
uv run --extra dev pytest
```

Check compilation:

```powershell
uv run --extra dev python -m compileall src tests
```

### Release-style local validation

```powershell
uv lock --offline
uv run --offline --extra dev pytest
uv run --offline --extra dev python -m compileall src tests
$env:UV_OFFLINE='1'; .\build_exe_windows.bat
```

### GitHub Actions

The repository includes two workflows:

- `.github/workflows/ci.yml` for Windows CI on push and pull request
- `.github/workflows/release-windows.yml` for rebuilding `LIMUZIN_GRID_MANAGER.exe` as a GitHub Actions artifact

These workflows complement local validation, but they do not replace manual user testing before release publication.

## Repository structure

```text
.
├── src/limuzin_grid_manager/
│   ├── app/                      # export, projects, point import/export, runtime helpers
│   ├── core/                     # geometry, CRS, zones, KML/SVG/GeoJSON/CSV, numbering
│   └── ui/                       # PySide6 windows, preview, themes
├── tests/                        # automated tests
├── versions/                     # version notes and archived planning documents
│   └── roadmaps_archive/         # historical roadmaps and completed execution plans
├── GRIDBASE.md                   # technical base documentation
├── USER_GUIDE.md                 # end-user guide
├── GITHUB.md                     # git, release, and publication rules
├── build_exe_windows.bat         # Windows EXE build
├── pyproject.toml                # package metadata and dependencies
└── uv.lock                       # dependency lock file
```

## Documentation map

- [`USER_GUIDE.md`](USER_GUIDE.md) - end-user instructions and manual check flow
- [`GRIDBASE.md`](GRIDBASE.md) - technical source of truth for behavior and architecture
- [`GITHUB.md`](GITHUB.md) - release workflow, CI, tag, and publication rules
- [`versions/GRIDVERSIONS.md`](versions/GRIDVERSIONS.md) - version index
- [`versions/v2.2.0.md`](versions/v2.2.0.md) - release notes for the current stable version
- [`versions/roadmaps_archive/roadmap.md`](versions/roadmaps_archive/roadmap.md) - archived roadmap up to `v1.0`
- [`versions/roadmaps_archive/ROADMAPv2.md`](versions/roadmaps_archive/ROADMAPv2.md) - archived roadmap for `v1.0 -> v2.0`
- [`versions/roadmaps_archive/ROADMAPv2.1.md`](versions/roadmaps_archive/ROADMAPv2.1.md) - archived roadmap for `v2.0 -> v2.1`
- [`versions/roadmaps_archive/FIXPROD.md`](versions/roadmaps_archive/FIXPROD.md) - archived production hardening plan up to `v2.2.0`

## License

MIT. See [`LICENSE`](LICENSE).
