@echo off
title Ace Combat Online - TDM Runner

echo =======================================================
echo          Ace Combat Online - TDM Automation Runner
echo =======================================================
echo.
echo [Tips] Please ensure the game is running in 1280x720 window mode.
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

python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%

echo.
pause
