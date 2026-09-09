@echo off
cd /d "%~dp0"
py -3.11 setup_backend.py
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo Setup failed. See the error above and INSTALL.txt.
pause
exit /b %RESULT%
