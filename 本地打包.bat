@echo off
title MAAACOL - 本地打包构建助手

echo =======================================================
echo            MAAACOL 本地打包构建助手
echo =======================================================
echo.

:: 检查 Python 是否可用
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到 Python 环境，请确保已安装 Python 并加入系统 PATH！
    echo.
    pause
    exit /b 1
)

echo 请选择打包构建模式：
echo   [1] 极速本地打包 (推荐，复用本地运行环境，无需联网，几秒内完成)
echo   [2] 全新干净构建 (从 GitHub 下载最新 MaaFramework 与 MFAAvalonia 纯净组装)
echo   [3] 快速同步资源到 gui/ 目录 (将最新流水线与脚本同步至本地测试目录)
echo   [4] 退出
echo.

set /p CHOICE="请输入选项 [默认 1]: "
if "%CHOICE%"=="" set CHOICE=1

if "%CHOICE%"=="1" (
    echo.
    echo =======================================================
    echo 正在执行：极速本地打包...
    echo =======================================================
    python tools\build_local.py --mode local --open-dir
    goto DONE
)

if "%CHOICE%"=="2" (
    echo.
    echo =======================================================
    echo 正在执行：全新干净构建...
    echo =======================================================
    set /p PROXY_INPUT="是否使用 GitHub 镜像加速？[直接回车使用 https://ghproxy.net/，输入 n 不使用]: "
    if "%PROXY_INPUT%"=="" set PROXY_OPT=--proxy https://ghproxy.net/
    if "%PROXY_INPUT%"=="n" set PROXY_OPT=
    if "%PROXY_INPUT%"=="N" set PROXY_OPT=

    python tools\build_local.py --mode clean %PROXY_OPT% --open-dir
    goto DONE
)

if "%CHOICE%"=="3" (
    echo.
    echo =======================================================
    echo 正在同步最新资源与脚本到 gui/ ...
    echo =======================================================
    python tools\build_local.py --mode sync-gui
    goto DONE
)

if "%CHOICE%"=="4" (
    exit /b 0
)

:DONE
echo.
pause
