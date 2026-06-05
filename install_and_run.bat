@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  Eden Seed Decoder - Install and Run
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo Found Python %PYVER%

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [1/4] Creating virtual environment .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) else (
    echo.
    echo [1/4] Virtual environment exists, skipping creation.
)

echo.
echo [2/4] Upgrading pip / setuptools / wheel ...
".venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [ERROR] Failed to upgrade pip.
    pause
    exit /b 1
)

echo.
echo [3/4] Installing project with [fast] extras ...
".venv\Scripts\python.exe" -m pip install -e ".[fast]"
if errorlevel 1 (
    echo [ERROR] Installation failed.
    pause
    exit /b 1
)

echo.
echo [4/4] Starting web UI ...
echo Open in browser: http://127.0.0.1:8765
echo Press Ctrl+C to stop
echo.

".venv\Scripts\eden-seed-decoder.exe" --web
if errorlevel 1 (
    ".venv\Scripts\python.exe" predict_eden.py --web
)

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start web UI.
    pause
    exit /b 1
)

endlocal
