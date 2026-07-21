@echo off
setlocal
cd /d "%~dp0"
py -3 -m PyInstaller --noconfirm --clean ActPilot.spec
if errorlevel 1 exit /b %errorlevel%
echo.
echo Build ready: dist\ActPilot-PoE1.exe
