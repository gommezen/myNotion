#!/usr/bin/env bash
# =============================================================================
# MyNotion Quality Gate — Staged quality checks for pre-commit/pre-push
# =============================================================================
#
# Usage:
#   ./scripts/quality_check.sh          # Run all stages
#   ./scripts/quality_check.sh --quick  # Lint + type check only (skip tests)
#   ./scripts/quality_check.sh --fix    # Auto-fix what ruff can handle
#
# Exit codes:
#   0 = all stages passed
#   1 = one or more stages failed
#
# Stages run in order of speed (fastest first, fail-fast):
#   1. Formatting check  (ruff format --check)
#   2. Linting           (ruff check)
#   3. Type checking      (mypy)
#   4. Unit tests         (pytest, skipped with --quick)
# =============================================================================

set -euo pipefail

# --- Configuration -----------------------------------------------------------
# Root of the project (one level up from scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="${PROJECT_ROOT}/src"
TEST_DIR="${PROJECT_ROOT}/tests"

# Colors for terminal output (disabled if not a TTY)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' BLUE='' BOLD='' RESET=''
fi

# --- Parse arguments ---------------------------------------------------------
QUICK=false
FIX=false
for arg in "$@"; do
    case "$arg" in
        --quick) QUICK=true ;;
        --fix)   FIX=true ;;
        --help|-h)
            echo "Usage: $0 [--quick] [--fix]"
            echo "  --quick  Skip tests, only run lint + type check"
            echo "  --fix    Auto-fix formatting and lint issues"
            exit 0
            ;;
        *) echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# --- Helper functions --------------------------------------------------------
STAGE=0
FAILURES=0

# Print a stage header with numbering
stage() {
    STAGE=$((STAGE + 1))
    echo ""
    echo -e "${BLUE}${BOLD}━━━ Stage ${STAGE}: $1 ━━━${RESET}"
}

# Print pass/fail result for a stage
pass() { echo -e "  ${GREEN}✓ $1${RESET}"; }
fail() { echo -e "  ${RED}✗ $1${RESET}"; FAILURES=$((FAILURES + 1)); }
skip() { echo -e "  ${YELLOW}⊘ $1 (skipped)${RESET}"; }
info() { echo -e "  ${BLUE}ℹ $1${RESET}"; }

# Check that a command exists, or print a helpful install hint
require() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}Error: '$1' not found.${RESET}"
        echo -e "Install dev dependencies: ${BOLD}pip install -r requirements-dev.txt${RESET}"
        exit 1
    fi
}

# --- Preflight ---------------------------------------------------------------
cd "${PROJECT_ROOT}"
echo -e "${BOLD}MyNotion Quality Gate${RESET}"
echo -e "Project root: ${PROJECT_ROOT}"

require ruff
require mypy
require pytest

# --- Stage 1: Formatting -----------------------------------------------------
stage "Formatting (ruff format)"

if [ "$FIX" = true ]; then
    # Auto-fix mode: apply formatting
    if ruff format "${SRC_DIR}" "${TEST_DIR}" 2>/dev/null; then
        pass "Formatted src/ and tests/"
    else
        fail "Formatting failed"
    fi
else
    # Check mode: report but don't change files
    if ruff format --check "${SRC_DIR}" "${TEST_DIR}" 2>/dev/null; then
        pass "All files correctly formatted"
    else
        fail "Formatting issues found — run with --fix to auto-format"
    fi
fi

# --- Stage 2: Linting --------------------------------------------------------
stage "Linting (ruff check)"

if [ "$FIX" = true ]; then
    # Auto-fix mode: apply safe fixes
    if ruff check --fix "${SRC_DIR}" "${TEST_DIR}" 2>/dev/null; then
        pass "Lint checks passed (auto-fixed where possible)"
    else
        fail "Lint errors remain after auto-fix — review manually"
    fi
else
    if ruff check "${SRC_DIR}" "${TEST_DIR}" 2>/dev/null; then
        pass "No lint issues"
    else
        fail "Lint issues found — run with --fix or review manually"
    fi
fi

# --- Stage 3: Type checking ---------------------------------------------------
stage "Type Checking (mypy)"

# mypy reads config from pyproject.toml [tool.mypy] section
if mypy "${SRC_DIR}" --ignore-missing-imports --no-error-summary 2>/dev/null; then
    pass "No type errors"
else
    fail "Type errors found"
fi

# --- Stage 4: Tests -----------------------------------------------------------
if [ "$QUICK" = true ]; then
    stage "Tests"
    skip "Skipped (--quick mode)"
else
    stage "Tests (pytest)"

    # Run with short traceback for cleaner output
    # --tb=short: concise tracebacks
    # -q: quiet mode (less boilerplate)
    # --no-header: skip pytest header
    if pytest "${TEST_DIR}" -q --tb=short --no-header 2>/dev/null; then
        pass "All tests passed"
    else
        fail "Test failures — run 'pytest tests/ -v' for details"
    fi
fi

# --- Summary ------------------------------------------------------------------
echo ""
echo -e "${BOLD}━━━ Summary ━━━${RESET}"

if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ All stages passed${RESET}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ ${FAILURES} stage(s) failed${RESET}"
    echo -e "${YELLOW}  Fix issues and re-run, or use --fix for auto-fixable problems${RESET}"
    exit 1
fi
