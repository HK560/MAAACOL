@echo off
chcp 65001 >nul
title Ace Combat Online - TDM Runner

echo =======================================================
echo          Ace Combat Online - TDM 自动化运行脚本
echo =======================================================
echo.
echo [提示] 请确保游戏运行在 1280x720 窗口分辨率下。
echo.

set ROUNDS=10
set MINUTES=60

set /p USER_ROUNDS="目标运行局数 [默认 10, 输入 0 为无限制]: "
if not "%USER_ROUNDS%"=="" set ROUNDS=%USER_ROUNDS%

set /p USER_MINUTES="最长运行分钟数 [默认 60, 输入 0 为无限制]: "
if not "%USER_MINUTES%"=="" set MINUTES=%USER_MINUTES%

echo.
echo 正在启动: 局数=%ROUNDS%, 最长=%MINUTES%分钟...
echo 按 Ctrl+C 可随时停止。
echo.

python run_tdm.py --rounds %ROUNDS% --minutes %MINUTES%

echo.
pause
