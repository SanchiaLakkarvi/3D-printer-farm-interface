#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE="$ROOT_DIR/tests/test_gcode_validator.py"

if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v py)"
elif [[ -x "/c/Users/hanng/AppData/Local/Programs/Thonny/python.exe" ]]; then
    PYTHON_BIN="/c/Users/hanng/AppData/Local/Programs/Thonny/python.exe"
else
    echo "ERROR: Python was not found."
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