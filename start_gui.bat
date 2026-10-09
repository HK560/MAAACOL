@echo off
title MAAACOL - Graphical Interface (GUI)

echo =======================================================
echo          Starting MAAACOL Graphical Interface (GUI)
echo =======================================================
echo.

:: Make a Python with the maafw binding available for the GUI Agent and CLI runner
call "%~dp0tools\ensure_agent_env.bat" "%~dp0."
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

:: Check if gui folder exists, otherwise attempt auto-setup from install/ or MFA/
if not exist "%~dp0gui\MAAACOL.exe" (
    if exist "%~dp0gui\MFAAvalonia.exe" (
        copy /y "%~dp0gui\MFAAvalonia.exe" "%~dp0gui\MAAACOL.exe" >nul
    ) else if exist "%~dp0install\MAAACOL.exe" (
        echo [INFO] Initializing gui folder from install folder...
        python "%~dp0tools\build_local.py" --mode sync-gui
    ) else if exist "%~dp0install\MFAAvalonia.exe" (
        echo [INFO] Initializing gui folder from install folder...
        python "%~dp0tools\build_local.py" --mode sync-gui
    ) else (
        echo [ERROR] GUI environment not found (gui\MAAACOL.exe)!
        echo.
        echo Please run 'build_local.bat' and select option [2] to download
        echo and prepare MaaFramework and MAAACOL GUI components.
        echo.
        pause
        exit /b 1
    )
)

:: Sync latest assets and scripts to gui folder
echo [INFO] Syncing latest assets and scripts to GUI environment...
python "%~dp0tools\build_local.py" --mode sync-gui >nul 2>&1

echo [INFO] Launching MAAACOL.exe...
:: Use the .NET runtime shipped in the package when present, so no host .NET install is required
if exist "%~dp0gui\runtime\shared" (
    set "DOTNET_ROOT=%~dp0gui\runtime"
    set "DOTNET_ROOT_X64=%~dp0gui\runtime"
)
cd /d "%~dp0gui"
if exist "%~dp0gui\MAAACOL.exe" (
    start "" "MAAACOL.exe"
) else (
    start "" "MFAAvalonia.exe"
)
