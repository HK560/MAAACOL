@echo off
title MAAACOL - Graphical Interface (GUI)

echo =======================================================
echo          Starting MAAACOL Graphical Interface (GUI)
echo =======================================================
echo.

:: Add local virtual environment to PATH if present
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PATH=%~dp0.venv\Scripts;%PATH%"
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    set "PATH=%~dp0..\.venv\Scripts;%PATH%"
)

:: Check if gui folder exists, otherwise attempt auto-setup from install/ or MFA/
if not exist "%~dp0gui\MFAAvalonia.exe" (
    if exist "%~dp0install\MFAAvalonia.exe" (
        echo [INFO] Initializing gui folder from install folder...
        python "%~dp0tools\build_local.py" --mode sync-gui
    ) else (
        echo [ERROR] GUI environment not found (gui\MFAAvalonia.exe)!
        echo.
        echo Please run 'build_local.bat' and select option [2] to download
        echo and prepare MaaFramework and MFAAvalonia components.
        echo.
        pause
        exit /b 1
    )
)

:: Sync latest assets and scripts to gui folder
echo [INFO] Syncing latest assets and scripts to GUI environment...
python "%~dp0tools\build_local.py" --mode sync-gui >nul 2>&1

echo [INFO] Launching MFAAvalonia.exe...
cd /d "%~dp0gui"
start "" "MFAAvalonia.exe"
