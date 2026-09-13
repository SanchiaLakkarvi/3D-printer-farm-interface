G-code Validation

This module validates uploaded 3D printer G-code files before printer selection.

It is designed for the 3D-printer-farm-interface project and checks whether an uploaded file is valid and compatible with one of the supported Prusa printer profiles.

Supported files

.gcode

.bgcode

The validator checks the file contents as well as the extension, so renaming an unrelated file to .gcode or .bgcode will not make it valid.

Supported printer profiles

Current configured profiles:

Prusa CORE One HF0.4 nozzle

Original Prusa XL - 5T Input Shaper 0.4 nozzle

The same uploaded file is checked against both profiles. A file passes only when exactly one supported profile matches.

Validation flow

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

The validator does not queue or start a print. A successful result only moves the workflow to printer selection.

Main checks

1. File format

Checks:

file exists

file is not empty

extension is supported

.gcode contains readable text G-code

.bgcode contains the expected binary G-code header

extension and content type match

2. Parse and integrity

For text .gcode:

reads the full file

verifies executable G/M/T commands exist

checks the PrusaSlicer configuration block

detects incomplete/truncated configuration

checks required end-of-print shutdown commands

For .bgcode:

validates binary structure

checks block sizes

verifies CRC32 checksums when present

reads available metadata blocks

confirms executable G-code blocks exist

3. Metadata

Important fields include:

printer_model

printer_variant

printer_settings_id

nozzle_diameter

nozzle_high_flow

filament_type

filament_abrasive

bed_shape

max_print_height

max_layer_z

temperature

bed_temperature

first-layer temperatures

filament usage

estimated print time

The validator also detects conflicting critical metadata.

4. M862 executable cross-check

For text Prusa G-code, metadata is cross-checked against executable compatibility commands.

Important commands include:

M862.1
M862.3
M862.5
M862.6

Examples:

M862.1 — nozzle and related compatibility information

M862.3 — printer model

M862.5 — G-code compatibility level

M862.6 — required firmware/printer features such as Input Shaper

This prevents the validator from trusting editable metadata comments alone.

5. Printer compatibility

The upload is checked against both configured printer profiles.

Checks include:

printer model

printer variant

printer settings/profile

nozzle diameter

high-flow requirement

material metadata

build volume

maximum print height

nozzle temperature

bed temperature

If no profile matches, the user must re-slice or upload another G-code file.

If more than one profile matches, validation fails because the configuration is ambiguous.

Result

A successful validation returns a structured result similar to:

{
  "status": "PASS",
  "passed": true,
  "compatible_profile": "core_one_hf04",
  "compatible_printer": "Prusa CORE One HF0.4 nozzle",
  "required_material": "PLA",
  "next_step": "SELECT_PRINTER"
}

A failed validation reports:

failed validation stage

reason/error

printer checks

compatible profiles, if any

next step

Example:

{
  "status": "FAIL",
  "passed": false,
  "failed_stage": 4,
  "next_step": "UPLOAD_GCODE"
}
