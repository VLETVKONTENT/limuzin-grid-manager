# User Guide: LIMUZIN GRID MANAGER

Version: `v2.2.0`

This guide is for normal daily work in the application: building grids, exporting files, working with points from Excel, and checking the most important behaviors before handing the result to a user.

## 1. Prepare the area

In the `Coordinates, meters` block, enter two points:

- `NW X`, `NW Y` - upper-left point
- `SE X`, `SE Y` - lower-right point

Coordinates must be entered in SK-42 / Pulkovo-42, Gauss-Kruger, in meters.

Input rules:

- `X` is northing
- `Y` is easting
- spaces and decimal commas are accepted
- if the points are entered not strictly as NW and SE, the application normalizes the bounds automatically

## 2. Choose the grid

In the `Grid` block, enable what you need:

- `1000x1000` only
- `100x100` only
- both together

When both are enabled, the `100x100` grid is built inside each big `1000x1000` tile.

Also choose:

- rounding mode
- numbering mode for `100x100`
- start corner
- spiral direction when spiral numbering is used

## 3. Check preview and validation

Use the `Preview` tab to inspect the scheme before export.

Available actions:

- mouse wheel zoom
- drag to pan
- click a big tile to inspect it

Use the `Validation` tab to check:

- area dimensions
- rounded bounds
- zone information
- grid counts
- warnings
- blocking errors
- export summary

### Important zone rule

Areas spanning several Gauss-Kruger zones are allowed, but export is blocked if a single `1000x1000` or `100x100` cell crosses a zone boundary inside the cell.

If that happens:

- enable rounding, or
- adjust `Y` bounds so the zone boundary goes along the grid edge

Zones outside `1..32` also block export.

## 4. Configure names and style

`Configure 1000x1000 names` opens a table for renaming big tiles.

Rules:

- empty value keeps the default number
- renaming a big tile does not change small `100x100` numbers inside it
- ZIP archive entry names still stay `tile_###.kml`

`Configure KML style` lets you change:

- line color and width for `1000x1000`
- line color and width for `100x100`
- fill mode for `1000x1000`
- common fill color and opacity for all `100x100`

Default KML style remains conservative:

- black lines
- no fill
- `<fill>0</fill>`

## 5. Export the grid

Open the `Export` tab and choose format:

- `KML`
- `ZIP`
- `SVG`
- `GeoJSON`
- `CSV`

Then choose output path and generate the result.

### Format notes

- `KML` creates one common file
- `ZIP` is available only when `1000x1000` is enabled
- `ZIP` contains files named `tile_###.kml`
- `SVG` is useful for vector checking
- `GeoJSON` is useful for GIS tools
- `CSV` is useful for table-based verification

Long export operations show progress, support cancellation, and use atomic writing through a temporary file, so a failed export should not overwrite an existing good result.

## 6. Work with points from Excel

Open:

```text
Tools -> Points from Excel...
```

This opens a separate window that does not change the grid workflow.

### Expected Excel format

The first worksheet with data should contain columns:

```text
ФИО | Дата | Координаты
```

The app imports the workbook in the background, so the window stays responsive.

After import you can:

- review loaded rows
- review row-level errors
- choose point color and opacity
- choose output `.kml`
- generate point KML

Point export also runs in the background, shows progress, and supports cancellation.

## 7. Save and reopen projects

Use the `Project` menu or toolbar to:

- create a new project
- open `.lgm.json`
- save
- save as

Project file stores:

- coordinates
- grid configuration
- numbering
- big tile names
- KML style
- export settings

The save operation is atomic: the app writes to a temporary file first and replaces the final `.lgm.json` only after successful completion.

The last opened or saved project path is remembered locally through `QSettings`.

## 8. Runtime log

If the app, Excel import, or export fails unexpectedly, the error message should show the path to the runtime log.

Default location:

```text
%LOCALAPPDATA%\LIMUZIN GRID MANAGER\logs\runtime.log
```

Use this log when reporting a failure.

## 9. Manual smoke checklist

Before handing a new build to a user, check at least:

- app starts normally
- main window opens
- grid preview works
- validation reacts to invalid zone input
- KML export works
- ZIP export works when `1000x1000` is enabled
- SVG export works
- GeoJSON export works
- CSV export works
- multi-zone export works when cells align to zone boundaries
- export is blocked when a cell crosses a zone boundary inside itself
- project save and reopen work
- `Tools -> Points from Excel...` opens
- sample `.xlsx` imports without freezing the window
- point KML export works
- runtime log path is shown on forced failure

## 10. If you run from source

Install dependencies:

```powershell
uv sync --extra dev
```

Run the app:

```powershell
uv run limuzin-grid-manager
```

Build EXE:

```powershell
.\build_exe_windows.bat
```
