#!/usr/bin/env bash

set -euo pipefail

VALIDATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$VALIDATION_DIR/.." && pwd)"
TEST_FILE="$VALIDATION_DIR/tests/test_gcode_validator.py"

# Prefer the project's virtual environment.
if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/Scripts/python.exe"

# Otherwise use an installed Python.
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"

elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"

elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v py)"

else
    echo "ERROR: Python was not found."
    echo "Install Python or create a .venv in the repository root."
    exit 1
fi

if [[ ! -f "$TEST_FILE" ]]; then
    echo "ERROR: Test file not found:"
    echo "  $TEST_FILE"
    exit 1
fi

echo "Using Python: $PYTHON_BIN"
echo "Running validation tests..."
echo

"$PYTHON_BIN" "$TEST_FILE"

echo
echo "Validation tests completed."