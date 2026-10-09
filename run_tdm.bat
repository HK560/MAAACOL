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

:: Make a Python with the maafw binding available for the GUI Agent and CLI runner
call "%~dp0tools\ensure_agent_env.bat" "%~dp0."
if errorlevel 1 (
    echo.
    pause
    exit /b 1
)

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
python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%

echo.
pause
