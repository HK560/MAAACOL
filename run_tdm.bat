@echo off
title Ace Combat Online - Multiplayer Battle Runner

echo =======================================================
echo        Ace Combat Online - Multiplayer Battle Runner
echo =======================================================
echo.
echo [Pre-requisite Instructions]
echo 1. Manually enter Multiplayer mode in game.
echo 2. Choose your desired game mode (any mode supported).
echo 3. Return to Multiplayer Lobby (where your character can freely move).
echo 4. Configure rounds and max duration below to start.
echo [Recommendation] Strongly recommend setting game to Windowed 1280x720 resolution.
echo.

set ROUNDS=10
set MINUTES=60

set /p USER_ROUNDS="Target rounds [Default 10, 0 for unlimited]: "
if not "%USER_ROUNDS%"=="" set ROUNDS=%USER_ROUNDS%

set /p USER_MINUTES="Max minutes [Default 60, 0 for unlimited]: "
if not "%USER_MINUTES%"=="" set MINUTES=%USER_MINUTES%

echo.
echo Starting: rounds=%ROUNDS%, max_minutes=%MINUTES%...
echo Press Ctrl+C anytime to stop.
echo.

set PYTHONUNBUFFERED=1
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%
) else if exist "%~dp0..\.venv\Scripts\python.exe" (
    "%~dp0..\.venv\Scripts\python.exe" run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%
) else (
    python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%
)

echo.
pause
