@echo off
REM Build MyNotion as a standalone Windows executable.
REM Usage: scripts\build.bat

setlocal

set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo ============================================
echo  Building MyNotion
echo ============================================
echo.

REM Check PyInstaller is available
where pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PyInstaller not found. Install it with:
    echo   pip install pyinstaller
    exit /b 1
)

REM Clean previous build artifacts
if exist build\MyNotion rd /s /q build\MyNotion
if exist dist\MyNotion.exe del /q dist\MyNotion.exe

echo Running PyInstaller...
echo.
pyinstaller MyNotion.spec --noconfirm

if %errorlevel% neq 0 (
    echo.
    echo ============================================
    echo  BUILD FAILED
    echo ============================================
    exit /b 1
)

echo.
echo ============================================
echo  BUILD SUCCESSFUL
echo ============================================
echo.
echo Output: %PROJECT_ROOT%\dist\MyNotion.exe
echo.
echo To test: dist\MyNotion.exe
echo To install: scripts\install.bat

endlocal
