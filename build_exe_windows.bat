@echo off
setlocal

REM Build standalone Windows EXE for the PySide6 version.

uv sync --extra dev
if errorlevel 1 exit /b %errorlevel%

for /f "delims=" %%i in ('uv run python -c "from pyproj import datadir; print(datadir.get_data_dir())"') do set "PROJ_DATA=%%i"

uv run pyinstaller --noconfirm --clean --onefile --windowed ^
  --name "LIMUZIN_GRID_MANAGER" ^
  --paths "src" ^
  --icon "icon.ico" ^
  --version-file "version_info.txt" ^
  --manifest "app.manifest" ^
  --add-data "icon.ico;." ^
  --add-data "icon.png;." ^
  --add-data "app.manifest;." ^
  --add-data "%PROJ_DATA%;pyproj\proj_dir\share\proj" ^
  --collect-submodules openpyxl ^
  --collect-data openpyxl ^
  --collect-data pyproj ^
  src\limuzin_grid_manager\__main__.py
if errorlevel 1 exit /b %errorlevel%

echo.
echo Done. Check dist\LIMUZIN_GRID_MANAGER.exe
