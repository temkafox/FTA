@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if "%~1"=="" goto :usage
set "RELEASE_VERSION=%~1"
if /I "%RELEASE_VERSION:~0,1%"=="v" set "RELEASE_VERSION=%RELEASE_VERSION:~1%"

echo %RELEASE_VERSION%| findstr /R /X "[0-9][0-9]*\.[0-9][0-9]*\.[0-9][0-9]*" >nul
if errorlevel 1 (
    echo ERROR: version must look like 1.2.3
    exit /b 2
)

where git >nul 2>nul || (echo ERROR: Git was not found in PATH. & exit /b 1)
where py >nul 2>nul || (echo ERROR: Python launcher ^(py^) was not found in PATH. & exit /b 1)

for /f "delims=" %%B in ('git branch --show-current') do set "CURRENT_BRANCH=%%B"
if not defined CURRENT_BRANCH (echo ERROR: detached HEAD is not supported. & exit /b 1)

git rev-parse -q --verify "refs/tags/v%RELEASE_VERSION%" >nul 2>nul && (echo ERROR: tag v%RELEASE_VERSION% already exists locally. & exit /b 1)
git ls-remote origin >nul
if errorlevel 1 (
    echo ERROR: origin is unavailable. Fix the remote URL or GitHub authentication first.
    exit /b 1
)

py -3 set_version.py "%RELEASE_VERSION%"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [1/4] Building ActPilot v%RELEASE_VERSION%...
call build.bat
if errorlevel 1 (echo ERROR: build failed. Nothing was committed or tagged. & exit /b 1)
if not exist "dist\ActPilot-PoE1.exe" (echo ERROR: dist\ActPilot-PoE1.exe was not created. & exit /b 1)

echo.
echo [2/4] Creating release commit...
git add -A
git diff --cached --quiet && (echo ERROR: there are no changes to commit. & exit /b 1)
git commit -m "Release v%RELEASE_VERSION%"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [3/4] Creating tag v%RELEASE_VERSION%...
git tag -a "v%RELEASE_VERSION%" -m "ActPilot v%RELEASE_VERSION%"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [4/4] Pushing commit and tag to origin...
git push --atomic origin "%CURRENT_BRANCH%" "v%RELEASE_VERSION%"
if errorlevel 1 (
    echo ERROR: push failed. The commit and tag remain local.
    echo Fix GitHub authentication, then run:
    echo   git push --atomic origin %CURRENT_BRANCH% v%RELEASE_VERSION%
    exit /b 1
)

echo.
echo SUCCESS: v%RELEASE_VERSION% was pushed.
echo GitHub Actions is now building and publishing the Release.
echo Local build: dist\ActPilot-PoE1.exe
exit /b 0

:usage
echo Usage: release.bat VERSION
echo Example: release.bat 1.2.3
exit /b 2
