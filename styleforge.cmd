@echo off
REM styleforge one-click launcher for Windows (no POSIX shell required).
REM Usage:  styleforge.cmd install [pack]
REM         styleforge.cmd uninstall
REM         styleforge.cmd status
setlocal

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY where python3 >nul 2>nul && set "PY=python3"

if not defined PY (
    echo 未找到 Python。请先安装 Python 3.10+ 并加入 PATH。 1>&2
    exit /b 127
)

if "%~1"=="" (
    %PY% "%SCRIPT_DIR%\styleforge.py" install --pack default
) else if /i "%~1"=="install" (
    if "%~2"=="" ( %PY% "%SCRIPT_DIR%\styleforge.py" install --pack default ) else ( %PY% "%SCRIPT_DIR%\styleforge.py" install --pack %~2 )
) else if /i "%~1"=="uninstall" (
    %PY% "%SCRIPT_DIR%\styleforge.py" uninstall
) else if /i "%~1"=="status" (
    %PY% "%SCRIPT_DIR%\styleforge.py" status
) else if /i "%~1"=="doctor" (
    %PY% "%SCRIPT_DIR%\styleforge.py" doctor
) else (
    %PY% "%SCRIPT_DIR%\styleforge.py" %*
)
exit /b %ERRORLEVEL%
