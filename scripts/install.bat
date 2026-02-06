@echo off
REM Install MyNotion to local user directory with Start Menu shortcut and PATH entry.
REM Usage: scripts\install.bat
REM
REM What this does:
REM   1. Copies MyNotion.exe to %LOCALAPPDATA%\MyNotion\
REM   2. Creates a Start Menu shortcut (so Windows Search finds it)
REM   3. Adds install directory to user PATH (so "mynotion" works from terminal)

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0.."
set "EXE_SOURCE=%PROJECT_ROOT%\dist\MyNotion.exe"
set "INSTALL_DIR=%LOCALAPPDATA%\MyNotion"
set "START_MENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

echo ============================================
echo  Installing MyNotion
echo ============================================
echo.

REM Check the exe exists
if not exist "%EXE_SOURCE%" (
    echo ERROR: MyNotion.exe not found at:
    echo   %EXE_SOURCE%
    echo.
    echo Run scripts\build.bat first to build the executable.
    exit /b 1
)

REM Create install directory
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy exe
echo Copying MyNotion.exe to %INSTALL_DIR%...
copy /y "%EXE_SOURCE%" "%INSTALL_DIR%\MyNotion.exe" >nul
if %errorlevel% neq 0 (
    echo ERROR: Failed to copy executable.
    exit /b 1
)
echo   Done.
echo.

REM Copy icon for the shortcut
if exist "%PROJECT_ROOT%\resources\mynotion.ico" (
    copy /y "%PROJECT_ROOT%\resources\mynotion.ico" "%INSTALL_DIR%\mynotion.ico" >nul
)

REM Create Start Menu shortcut using PowerShell
echo Creating Start Menu shortcut...
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $shortcut = $ws.CreateShortcut('%START_MENU%\MyNotion.lnk'); $shortcut.TargetPath = '%INSTALL_DIR%\MyNotion.exe'; $shortcut.WorkingDirectory = '%INSTALL_DIR%'; $shortcut.Description = 'MyNotion - Text and Code Editor'; $iconPath = '%INSTALL_DIR%\mynotion.ico'; if (Test-Path $iconPath) { $shortcut.IconLocation = $iconPath }; $shortcut.Save()"
if %errorlevel% neq 0 (
    echo   WARNING: Could not create Start Menu shortcut.
) else (
    echo   Done. You can now find MyNotion in Windows Search.
)
echo.

REM Add to user PATH if not already there
echo Checking PATH...
echo %PATH% | findstr /i /c:"%INSTALL_DIR%" >nul 2>&1
if %errorlevel% equ 0 (
    echo   Already in PATH.
) else (
    echo   Adding %INSTALL_DIR% to user PATH...
    powershell -NoProfile -Command "$currentPath = [Environment]::GetEnvironmentVariable('Path', 'User'); if ($currentPath -notlike '*%INSTALL_DIR%*') { [Environment]::SetEnvironmentVariable('Path', $currentPath + ';%INSTALL_DIR%', 'User'); Write-Host '  Done. Open a new terminal to use: mynotion' } else { Write-Host '  Already in user PATH.' }"
)

echo.
echo ============================================
echo  Installation Complete
echo ============================================
echo.
echo Install location: %INSTALL_DIR%\MyNotion.exe
echo Start Menu:       Search "MyNotion" in Windows
echo Terminal:         Open a new terminal and type "mynotion"
echo.

endlocal
