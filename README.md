# LIMUZIN GRID MANAGER

**Version:** `v0.0.1`  
**Platform:** Windows  
**Purpose:** KML grid generator for AlpineQuest

LIMUZIN GRID MANAGER builds `1000x1000` and `100x100` meter grids from two SK-42 / Pulkovo-42 Gauss-Kruger points and exports them to KML for AlpineQuest.

---

## What It Does

- Accepts two points: `NW` (top-left) and `SE` (bottom-right).
- Uses SK-42 / Pulkovo-42 Gauss-Kruger coordinates in meters.
- Treats `X` as northing and `Y` as easting.
- Converts coordinates to WGS84 for KML.
- Builds `1000x1000`, `100x100`, or combined grids.
- Numbers squares with optional snake ordering.
- Exports either:
  - one combined `.kml`;
  - a `.zip` with one `tile_###.kml` per `1000x1000` square.

KML style is intentionally simple: standard black outlines, no colored fill, no transparent colored polygons.

---

## Project Role Notes

The project idea, testing direction, and user workflow belong to the project author.

Important: the author of the project does not understand the internal code structure and does not maintain the architecture manually. The code structure and implementation were written by Codex (OpenAI) according to the author's requirements and feedback.

For future work, use:

- [`GRIDBASE.md`](GRIDBASE.md) as the technical project memory.
- [`versions/GRIDVERSIONS.md`](versions/GRIDVERSIONS.md) as the version index.
- `versions/v*.md` files as detailed version notes.

---

## Interface

The application uses a PySide6 desktop interface:

- left panel: coordinates, grid options, export mode;
- right panel: live validation, grid statistics, warnings and errors;
- bottom actions: check, generate, open output folder;
- export runs in a worker thread so the window does not freeze during large exports.

---

## Coordinate Logic

Gauss-Kruger zone is inferred from the easting:

```python
zone = int(abs(y) // 1_000_000)
epsg = 28400 + zone
```

The transformer uses:

- source CRS: `EPSG:28400 + zone`;
- destination CRS: `EPSG:4326`;
- `always_xy=True`.

Input order is `X, Y`, but `pyproj` receives `Y, X`:

```python
lon, lat = transformer.transform(y, x)
```

KML writes coordinates as:

```text
lon,lat,0
```

---

## Development

Install dependencies:

```powershell
uv sync --extra dev
```

Run from source:

```powershell
uv run limuzin-grid-manager
```

Run tests:

```powershell
uv run --extra dev pytest
```

Compile check:

```powershell
uv run --extra dev python -m compileall src tests
```

Build Windows EXE:

```powershell
.\build_exe_windows.bat
```

The built executable is created at:

```text
dist/LIMUZIN_GRID_MANAGER.exe
```

---

## Current Version

Current working version: `v0.0.1`.

See [`versions/v0.0.1.md`](versions/v0.0.1.md) for release notes.
