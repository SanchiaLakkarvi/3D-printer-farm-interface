#!/usr/bin/env bash
set -euo pipefail

VALIDATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$VALIDATION_DIR/.." && pwd)"
TEST_FILE="$VALIDATION_DIR/tests/test_gcode_validator.py"
VALIDATOR="$VALIDATION_DIR/gcode_validator.py"
DATA_DIR="$VALIDATION_DIR/data"

if [[ -x "$REPO_ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif [[ -x "$REPO_ROOT/.venv/Scripts/python.exe" ]]; then
    PYTHON_BIN="$REPO_ROOT/.venv/Scripts/python.exe"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
elif command -v py >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v py)"
else
    echo "ERROR: Python was not found."
    exit 1
fi

echo "Using Python: $PYTHON_BIN"
echo

echo "=== Running automated tests ==="
"$PYTHON_BIN" "$TEST_FILE"

run_case() {
    local label="$1"
    local file="$2"
    local expected_status="$3"
    local expected_stage="${4:-}"
    local expected_profile="${5:-}"

    echo
    echo "=== $label ==="

    if [[ ! -f "$file" ]]; then
        echo "ERROR: Missing file: $file"
        exit 1
    fi

    result="$("$PYTHON_BIN" "$VALIDATOR" "$file")"

    printf '%s' "$result" | "$PYTHON_BIN" -c '
import json, sys
d = json.load(sys.stdin)
expected_status = sys.argv[1]
expected_stage = sys.argv[2]
expected_profile = sys.argv[3]

print("Status          :", d.get("status"))
if d.get("passed"):
    print("Matched printer :", d.get("compatible_printer"))
    print("Profile         :", d.get("compatible_profile"))
    print("Material        :", d.get("required_material"))
    print("Next step       :", d.get("next_step"))
else:
    print("Failed stage    :", d.get("failed_stage"))
    errors = d.get("errors") or []
    if errors:
        print("Error           :", errors[0])
    print("Next step       :", d.get("next_step"))

if d.get("status") != expected_status:
    raise SystemExit("Unexpected status")
if expected_stage and str(d.get("failed_stage")) != expected_stage:
    raise SystemExit("Unexpected failed stage")
if expected_profile and d.get("compatible_profile") != expected_profile:
    raise SystemExit("Unexpected compatible profile")

print("Result          : EXPECTED")
' "$expected_status" "$expected_stage" "$expected_profile"
}

run_case "VALID CORE ONE" \
    "$DATA_DIR/Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.gcode" \
    "PASS" "" "core_one_hf04"

run_case "BROKEN: MISSING END" \
    "$DATA_DIR/broken_missing_end.gcode" \
    "FAIL" "2"

run_case "BROKEN: NO MATERIAL" \
    "$DATA_DIR/broken_no_material.gcode" \
    "FAIL" "3"

run_case "BROKEN: WRONG PRINTER" \
    "$DATA_DIR/broken_wrong_printer.gcode" \
    "FAIL" "4"

run_case "BROKEN: TOO HOT" \
    "$DATA_DIR/broken_too_hot.gcode" \
    "FAIL" "6"

echo
echo "All validation tests completed."