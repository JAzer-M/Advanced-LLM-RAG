@echo off
rem PaperLens launcher for Windows (source checkout). Keep this window open while using PaperLens.
setlocal
cd /d "%~dp0.."
set "PAPERLENS_URL=http://127.0.0.1:8849"

curl.exe --noproxy "*" --silent --fail --max-time 2 "%PAPERLENS_URL%/api/meta" >nul 2>&1
if not errorlevel 1 (
    echo PaperLens is already running. Opening %PAPERLENS_URL%
    start "" "%PAPERLENS_URL%"
    exit /b 0
)

if not exist ".venv\Scripts\python.exe" (
    echo Cannot find .venv\Scripts\python.exe. Follow docs\INSTALL_AND_START.md to create the environment first.
    pause
    exit /b 1
)

rem UTF-8 mode: project files are UTF-8, Windows defaults to the local code page otherwise.
set "PYTHONUTF8=1"
set "OMP_NUM_THREADS=1"
set "OPENBLAS_NUM_THREADS=1"
set "MKL_NUM_THREADS=1"
set "TOKENIZERS_PARALLELISM=false"
set "HF_HUB_DISABLE_XET=1"
rem Papers, settings and retrieval models live outside the checkout, like the packaged app.
if not defined PAPERLENS_DATA_DIR set "PAPERLENS_DATA_DIR=%LOCALAPPDATA%\PaperLens"

echo Starting PaperLens. The browser opens automatically; data folder: %PAPERLENS_DATA_DIR%
echo Press Ctrl+C or close this window to stop.
".venv\Scripts\python.exe" -B -u -c "from webui import server; server.serve(open_browser=True)"
if errorlevel 1 pause
