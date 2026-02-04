@echo off
REM =============================================================================
REM MyNotion Quality Gate — Windows batch version
REM =============================================================================
REM Usage:
REM   scripts\quality_check.bat          # Run all stages
REM   scripts\quality_check.bat --quick  # Lint + type check only (skip tests)
REM   scripts\quality_check.bat --fix    # Auto-fix what ruff can handle
REM =============================================================================

setlocal enabledelayedexpansion

set "PROJECT_ROOT=%~dp0.."
set "SRC_DIR=%PROJECT_ROOT%\src"
set "TEST_DIR=%PROJECT_ROOT%\tests"
set "QUICK=0"
set "FIX=0"
set "FAILURES=0"

REM Parse arguments
:parse_args
if "%~1"=="" goto start
if "%~1"=="--quick" set "QUICK=1"
if "%~1"=="--fix" set "FIX=1"
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
shift
goto parse_args

:show_help
echo Usage: %~nx0 [--quick] [--fix]
echo   --quick  Skip tests, only run lint + type check
echo   --fix    Auto-fix formatting and lint issues
exit /b 0

:start
echo.
echo ============================================
echo   MyNotion Quality Gate
echo ============================================
echo Project root: %PROJECT_ROOT%
echo.

REM Check required tools
where ruff >nul 2>&1 || (echo ERROR: ruff not found. Run: pip install -r requirements-dev.txt & exit /b 1)
where mypy >nul 2>&1 || (echo ERROR: mypy not found. Run: pip install -r requirements-dev.txt & exit /b 1)
where pytest >nul 2>&1 || (echo ERROR: pytest not found. Run: pip install -r requirements-dev.txt & exit /b 1)

REM Stage 0: Import validation (catches runtime import errors)
echo.
echo === Stage 0: Import Validation ===
cd /d "%PROJECT_ROOT%\src"
python -c "from ui.main_window import MainWindow; print('  [OK] All imports valid')"
if !errorlevel! neq 0 (
    echo   [FAIL] Import errors - fix before continuing
    exit /b 1
)
cd /d "%PROJECT_ROOT%"

REM Stage 1: Formatting
echo.
echo === Stage 1: Formatting (ruff format) ===
if "%FIX%"=="1" (
    ruff format "%SRC_DIR%" "%TEST_DIR%"
    if !errorlevel! equ 0 (
        echo   [OK] Formatted src/ and tests/
    ) else (
        echo   [FAIL] Formatting failed
        set /a FAILURES+=1
    )
) else (
    ruff format --check "%SRC_DIR%" "%TEST_DIR%"
    if !errorlevel! equ 0 (
        echo   [OK] All files correctly formatted
    ) else (
        echo   [FAIL] Formatting issues found - run with --fix
        set /a FAILURES+=1
    )
)

REM Stage 2: Linting
echo.
echo === Stage 2: Linting (ruff check) ===
if "%FIX%"=="1" (
    ruff check --fix "%SRC_DIR%" "%TEST_DIR%"
    if !errorlevel! equ 0 (
        echo   [OK] Lint checks passed
    ) else (
        echo   [FAIL] Lint errors remain after auto-fix
        set /a FAILURES+=1
    )
) else (
    ruff check "%SRC_DIR%" "%TEST_DIR%"
    if !errorlevel! equ 0 (
        echo   [OK] No lint issues
    ) else (
        echo   [FAIL] Lint issues found - run with --fix
        set /a FAILURES+=1
    )
)

REM Stage 3: Type checking
echo.
echo === Stage 3: Type Checking (mypy) ===
mypy "%SRC_DIR%" --ignore-missing-imports --no-error-summary
if !errorlevel! equ 0 (
    echo   [OK] No type errors
) else (
    echo   [FAIL] Type errors found
    set /a FAILURES+=1
)

REM Stage 4: Tests
echo.
if "%QUICK%"=="1" (
    echo === Stage 4: Tests ===
    echo   [SKIP] Skipped --quick mode
) else (
    echo === Stage 4: Tests (pytest) ===
    pytest "%TEST_DIR%" -q --tb=short --no-header
    if !errorlevel! equ 0 (
        echo   [OK] All tests passed
    ) else (
        echo   [FAIL] Test failures
        set /a FAILURES+=1
    )
)

REM Summary
echo.
echo ============================================
if %FAILURES% equ 0 (
    echo   All stages passed!
    exit /b 0
) else (
    echo   %FAILURES% stage(s) failed
    exit /b 1
)
