# G-code Validation

This module validates uploaded 3D printer G-code files before printer selection.

It is designed for the **3D-printer-farm-interface** project and checks whether an uploaded file is valid and compatible with one of the supported Prusa printer profiles.

## Supported Files

- `.gcode`
- `.bgcode`

The validator checks the file content as well as the extension, so renaming an unrelated file to `.gcode` or `.bgcode` will not make it valid.

## Supported Printer Profiles

Current configured profiles:

- **Prusa CORE One HF0.4 nozzle**
- **Original Prusa XL - 5T Input Shaper 0.4 nozzle**

The same uploaded file is checked against both profiles.

A file passes validation only when exactly one supported printer profile matches.

## Validation Flow

```text
UPLOAD G-CODE
    |
    v
1. FILE FORMAT VALIDATION
    |
    v
2. PARSE + INTEGRITY
    |
    v
3. READ METADATA
    |
    v
4. M862 EXECUTABLE CROSS-CHECK
    |
    v
5. CHECK BOTH PRINTER PROFILES
   + build volume
   + nozzle configuration
   + temperature limits
    |
    v
6. EXACTLY ONE SUPPORTED PROFILE?
    |
    +-- YES --> PASS --> SELECT_PRINTER
    |
    +-- NO  --> FAIL --> UPLOAD_GCODE / RE-SLICE


## Run Validation Tests

The validation test suite can be run using the provided Bash script:

```bash
bash validation/test_validation.sh