@echo off
setlocal EnableExtensions

REM Build standalone Windows EXE for the PySide6 version.
REM By default the build stays unsigned for local development.
REM To sign the public release, set:
REM   LGM_SIGN_EXE=1
REM   LGM_SIGN_PFX_PATH=C:\path\to\certificate.pfx
REM   LGM_SIGN_PFX_PASSWORD=...
REM Optional:
REM   LGM_SIGN_TIMESTAMP_URL=http://timestamp.digicert.com

set "SIGN_REQUESTED=0"
if /I "%LGM_SIGN_EXE%"=="1" set "SIGN_REQUESTED=1"
if /I "%LGM_SIGN_EXE%"=="true" set "SIGN_REQUESTED=1"
if /I "%LGM_SIGN_EXE%"=="yes" set "SIGN_REQUESTED=1"

if "%SIGN_REQUESTED%"=="1" (
  if not defined LGM_SIGN_PFX_PATH (
    echo ERROR: Signing was requested, but LGM_SIGN_PFX_PATH is not set.
    exit /b 1
  )
  if not exist "%LGM_SIGN_PFX_PATH%" (
    echo ERROR: Signing was requested, but the certificate file was not found:
    echo   %LGM_SIGN_PFX_PATH%
    exit /b 1
  )
  if not defined LGM_SIGN_PFX_PASSWORD (
    echo ERROR: Signing was requested, but LGM_SIGN_PFX_PASSWORD is not set.
    exit /b 1
  )
  if not defined LGM_SIGN_TIMESTAMP_URL set "LGM_SIGN_TIMESTAMP_URL=http://timestamp.digicert.com"
  call :find_signtool
  if errorlevel 1 exit /b 1
) else (
  echo Building unsigned EXE. Set LGM_SIGN_EXE=1 with signing variables for the final public release.
)

if "%SIGN_REQUESTED%"=="1" (
  echo Signing requested. Signtool preflight passed:
  echo   %SIGNTOOL_EXE%
)

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

if "%SIGN_REQUESTED%"=="1" (
  call :sign_exe
  if errorlevel 1 exit /b 1
  echo.
  echo Signed EXE is ready: dist\LIMUZIN_GRID_MANAGER.exe
  exit /b 0
)

echo.
echo Unsigned EXE is ready: dist\LIMUZIN_GRID_MANAGER.exe
echo This artifact is suitable for local testing, but not for the final public release.
exit /b 0

:find_signtool
set "SIGNTOOL_EXE="
where /q signtool.exe
if not errorlevel 1 (
  for /f "delims=" %%i in ('where signtool.exe') do (
    set "SIGNTOOL_EXE=%%i"
    goto :signtool_found
  )
)

for /f "delims=" %%i in ('powershell -NoProfile -Command "$roots=@($env:ProgramFiles,$env:''ProgramFiles(x86)'') ^| Where-Object { $_ }; $kitRoots=$roots ^| ForEach-Object { Join-Path $_ ''Windows Kits'' }; $match=Get-ChildItem -Path $kitRoots -Filter signtool.exe -Recurse -ErrorAction SilentlyContinue ^| Sort-Object FullName -Descending ^| Select-Object -First 1 -ExpandProperty FullName; if($match){ Write-Output $match }"') do set "SIGNTOOL_EXE=%%i"

:signtool_found
if not defined SIGNTOOL_EXE (
  echo ERROR: Signing was requested, but signtool.exe could not be found.
  exit /b 1
)
exit /b 0

:sign_exe
set "TARGET_EXE=dist\LIMUZIN_GRID_MANAGER.exe"
if not exist "%TARGET_EXE%" (
  echo ERROR: Build finished, but %TARGET_EXE% was not found for signing.
  exit /b 1
)

"%SIGNTOOL_EXE%" sign ^
  /fd SHA256 ^
  /td SHA256 ^
  /tr "%LGM_SIGN_TIMESTAMP_URL%" ^
  /f "%LGM_SIGN_PFX_PATH%" ^
  /p "%LGM_SIGN_PFX_PASSWORD%" ^
  "%TARGET_EXE%"
if errorlevel 1 exit /b %errorlevel%

powershell -NoProfile -Command "$sig = Get-AuthenticodeSignature 'dist\\LIMUZIN_GRID_MANAGER.exe'; if ($sig.Status -ne 'Valid') { Write-Host ('ERROR: Authenticode verification failed: ' + $sig.Status); exit 1 }; Write-Host ('Authenticode status: ' + $sig.Status); if ($sig.SignerCertificate) { Write-Host ('Signer: ' + $sig.SignerCertificate.Subject) }"
if errorlevel 1 exit /b %errorlevel%
exit /b 0
