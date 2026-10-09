@echo off
title MAAACOL - Local Package Builder

echo =======================================================
echo            MAAACOL Local Package Builder
echo =======================================================
echo.

:: Check Python environment
set "PY_CMD=python"
if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_CMD=%~dp0.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found! Please ensure Python is installed and added to PATH.
        echo.
        pause
        exit /b 1
    )
)

echo Select build mode:
echo   [1] Fast Local Build (Recommended, reuse local env, no download, takes ~5s)
echo   [2] Clean Full Build (Download latest MaaFramework and MFAAvalonia from GitHub)
echo   [3] Fast Sync to gui/ (Sync latest resource and scripts to local dev folder)
echo   [4] Setup gui/ Environment (Download and configure local GUI runtime)
echo   [5] Exit
echo.

set /p CHOICE="Enter choice [Default 1]: "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo.
    echo =======================================================
    echo Executing: Fast Local Build...
    echo =======================================================
    "%PY_CMD%" tools\build_local.py --mode local --open-dir
    goto DONE
)

if "%CHOICE%"=="2" (
    echo.
    echo =======================================================
    echo Executing: Clean Full Build...
    echo =======================================================
    set /p PROXY_INPUT="Use GitHub mirror proxy? [Enter for https://ghproxy.net/, 'n' for direct]: "
    if "%PROXY_INPUT%"=="" set PROXY_OPT=--proxy https://ghproxy.net/
    if "%PROXY_INPUT%"=="n" set PROXY_OPT=
    if "%PROXY_INPUT%"=="N" set PROXY_OPT=

    "%PY_CMD%" tools\build_local.py --mode clean %PROXY_OPT% --open-dir
    goto DONE
)

if "%CHOICE%"=="3" (
    echo.
    echo =======================================================
    echo Syncing latest assets and scripts to gui/...
    echo =======================================================
    "%PY_CMD%" tools\build_local.py --mode sync-gui
    goto DONE
)

if "%CHOICE%"=="4" (
    echo.
    echo =======================================================
    echo Setting up gui/ environment...
    echo =======================================================
    set /p PROXY_INPUT="Use GitHub mirror proxy? [Enter for https://ghproxy.net/, 'n' for direct]: "
    if "%PROXY_INPUT%"=="" set PROXY_OPT=--proxy https://ghproxy.net/
    if "%PROXY_INPUT%"=="n" set PROXY_OPT=
    if "%PROXY_INPUT%"=="N" set PROXY_OPT=

    "%PY_CMD%" tools\build_local.py --mode setup-gui %PROXY_OPT%
    goto DONE
)

if "%CHOICE%"=="5" (
    exit /b 0
)

:DONE
echo.
pause
