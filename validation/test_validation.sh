#!/usr/bin/env bash
set -uo pipefail

VALIDATION_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$VALIDATION_DIR/.." && pwd)"
TEST_FILE="$VALIDATION_DIR/tests/test_gcode_validator.py"
VALIDATOR="$VALIDATION_DIR/gcode_validator.py"
DATA_DIR="$VALIDATION_DIR/data"

# Prefer the repository virtual environment.
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

if [[ ! -f "$TEST_FILE" ]]; then
    echo "ERROR: Test file not found: $TEST_FILE"
    exit 1
fi

if [[ ! -f "$VALIDATOR" ]]; then
    echo "ERROR: Validator not found: $VALIDATOR"
    exit 1
fi

FAILURES=0

echo "Using Python: $PYTHON_BIN"
echo
echo "========================================"
echo "1. Running automated unit tests"
echo "========================================"

if "$PYTHON_BIN" "$TEST_FILE"; then
    echo
    echo "Automated unit tests: PASS"
else
    echo
    echo "Automated unit tests: FAIL"
    FAILURES=$((FAILURES + 1))
fi

run_case() {
    local label="$1"
    local file="$2"
    local expected_status="$3"
    local expected_stage="${4:-}"
    local expected_profile="${5:-}"

    echo
    echo "========================================"
    echo "$label"
    echo "========================================"
    echo "File: $(basename "$file")"

    if [[ ! -f "$file" ]]; then
        echo "Result          : MISSING FILE"
        echo "Expected status : $expected_status"
        [[ -n "$expected_stage" ]] && echo "Expected stage  : $expected_stage"
        FAILURES=$((FAILURES + 1))
        return
    fi

    local result
    if ! result="$("$PYTHON_BIN" "$VALIDATOR" "$file")"; then
        echo "Result          : VALIDATOR EXECUTION ERROR"
        FAILURES=$((FAILURES + 1))
        return
    fi

    local check_output
    local check_status

    check_output="$(
        printf '%s' "$result" | "$PYTHON_BIN" -c '
import json
import sys

expected_status = sys.argv[1]
expected_stage = sys.argv[2]
expected_profile = sys.argv[3]

try:
    data = json.load(sys.stdin)
except Exception as exc:
    print(f"Could not parse validator output as JSON: {exc}")
    raise SystemExit(2)

actual_status = data.get("status")
actual_stage = data.get("failed_stage")
actual_profile = data.get("compatible_profile")

print(f"Status          : {actual_status}")

if data.get("passed"):
    print(f"Matched printer : {data.get('\''compatible_printer'\'')}")
    print(f"Profile         : {actual_profile}")
    print(f"Material        : {data.get('\''required_material'\'')}")
    print(f"Next step       : {data.get('\''next_step'\'')}")
else:
    print(f"Failed stage    : {actual_stage}")

    errors = data.get("errors") or []
    if errors:
        print(f"Error           : {errors[0]}")

    reasons = []
    for check in (data.get("printer_checks") or {}).values():
        reasons.extend(check.get("reasons") or [])

    if reasons:
        print(f"Reason          : {reasons[0]}")

    print(f"Next step       : {data.get('\''next_step'\'')}")

problems = []

if actual_status != expected_status:
    problems.append(
        f"expected status {expected_status}, got {actual_status}"
    )

if expected_stage and str(actual_stage) != expected_stage:
    problems.append(
        f"expected failed stage {expected_stage}, got {actual_stage}"
    )

if expected_profile and actual_profile != expected_profile:
    problems.append(
        f"expected profile {expected_profile}, got {actual_profile}"
    )

if problems:
    print("Result          : UNEXPECTED")
    for problem in problems:
        print(f"                  - {problem}")
    raise SystemExit(1)

print("Result          : EXPECTED")
' "$expected_status" "$expected_stage" "$expected_profile"
    )"
    check_status=$?

    printf '%s\n' "$check_output"

    if [[ $check_status -ne 0 ]]; then
        FAILURES=$((FAILURES + 1))
    fi
}

echo
echo "========================================"
echo "2. Running real G-code cases"
echo "========================================"

run_case \
    "VALID CORE ONE" \
    "$DATA_DIR/Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.gcode" \
    "PASS" \
    "" \
    "core_one_hf04"

run_case \
    "BROKEN: MISSING END" \
    "$DATA_DIR/broken_missing_end.gcode" \
    "FAIL" \
    "2"

run_case \
    "BROKEN: NO MATERIAL" \
    "$DATA_DIR/broken_no_material.gcode" \
    "FAIL" \
    "3"

run_case \
    "BROKEN: WRONG PRINTER" \
    "$DATA_DIR/broken_wrong_printer.gcode" \
    "FAIL" \
    "4"

run_case \
    "BROKEN: TOO HOT" \
    "$DATA_DIR/broken_too_hot.gcode" \
    "FAIL" \
    "6"

echo
echo "========================================"
echo "SUMMARY"
echo "========================================"

if [[ $FAILURES -eq 0 ]]; then
    echo "All validation cases behaved as expected."
    exit 0
else
    echo "$FAILURES test group(s) produced unexpected results."
    echo "All cases were still executed."
    exit 1
fi
