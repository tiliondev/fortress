@echo off
setlocal
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PREFIX=activate"
if /I "%~1"=="activate" set "PREFIX="
if /I "%~1"=="license" set "PREFIX="
where py.exe >nul 2>nul
if not errorlevel 1 goto activate_py
where python.exe >nul 2>nul
if not errorlevel 1 goto activate_python
>&2 echo Python 3 is required for activation. Install Python or set TILION_LICENSE_KEY.
exit /b 1
:activate_py
py.exe -3 -u "%~dp0tilion_activate.py" %PREFIX% %*
exit /b %ERRORLEVEL%
:activate_python
python.exe -u "%~dp0tilion_activate.py" %PREFIX% %*
exit /b %ERRORLEVEL%
