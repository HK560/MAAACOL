@echo off
:: Locate a Python interpreter that has the MaaFramework binding (maafw) installed,
:: then prepend its folder to PATH so "python" calls (GUI Agent / CLI runner) work.
:: The packaged python folder is tried first, so a released build needs no host Python.
:: Usage: call ensure_agent_env.bat "<package root, e.g. %~dp0.>"
setlocal EnableExtensions
set "ROOT=%~1"
if "%ROOT%"=="" set "ROOT=%~dp0."

set "MAAACOL_PY_EXE="
set "MAAACOL_PY_DIR="

call :probe "%ROOT%\python\python.exe"
if defined MAAACOL_PY_EXE goto :ready
call :probe "%ROOT%\.venv\Scripts\python.exe"
if defined MAAACOL_PY_EXE goto :ready
call :probe "%ROOT%\..\.venv\Scripts\python.exe"
if defined MAAACOL_PY_EXE goto :ready
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do call :probe "%%~fD\python.exe"
if defined MAAACOL_PY_EXE goto :ready
for /d %%D in ("%ProgramFiles%\Python3*") do call :probe "%%~fD\python.exe"
if defined MAAACOL_PY_EXE goto :ready
for /f "delims=" %%P in ('where python.exe 2^>nul') do call :probe "%%~fP"
if defined MAAACOL_PY_EXE goto :ready

echo [ERROR] No Python interpreter with the MaaFramework binding (maafw) was found.
echo [ERROR] The GUI Agent cannot start without it (GUI shows: Failed to LinkStart agentClient).
echo [ERROR] Install the dependency, then run this script again:
echo [ERROR]   Option 1 (keeps a local environment in this folder):
echo [ERROR]     python -m venv .venv
echo [ERROR]     .venv\Scripts\python.exe -m pip install -r requirements.txt
echo [ERROR]   Option 2 (installs into the current Python):
echo [ERROR]     python -m pip install -r requirements.txt
endlocal
exit /b 1

:ready
echo [INFO] Using Python with maafw: %MAAACOL_PY_EXE%
if not defined MAAACOL_PY_DIR goto :no_prefix
endlocal & set "PATH=%MAAACOL_PY_DIR%;%PATH%"
exit /b 0

:no_prefix
endlocal
exit /b 0

:probe
if "%~1"=="" exit /b 0
if defined MAAACOL_PY_EXE exit /b 0
if not exist "%~1" exit /b 0
for %%I in ("%~1") do if /i "%%~dpI"=="%LOCALAPPDATA%\Microsoft\WindowsApps\" exit /b 0
"%~1" -c "import maa" >nul 2>&1
if errorlevel 1 exit /b 0
for %%I in ("%~1") do set "MAAACOL_PY_DIR=%%~dpI"
set "MAAACOL_PY_EXE=%~1"
exit /b 0
