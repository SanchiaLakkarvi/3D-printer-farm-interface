# Two-printer G-code validator

This implementation follows exactly this order:

```text
Upload file
    |
    v
1. FILE FORMAT VALIDATION
    |
    +-- INVALID --> FAIL immediately
    |
    v
2. Parse G-code / BGCODE
    |
    +-- Cannot parse / corrupted --> FAIL
    |
    v
3. Read bottom/metadata information
    |
    v
4. Check the SAME file against BOTH printers
    |
    +--> Prusa CORE One HF0.4
    |
    +--> Original Prusa XL - 5T Input Shaper 0.4
    |
    v
5. Exactly one matches?
   YES --> PASS --> SELECT_PRINTER
   NO  --> FAIL --> UPLOAD_GCODE / re-slice
```

## Supported printer checks

### Prusa CORE One HF0.4 nozzle

- `printer_model = COREONE`
- `printer_variant = HF0.4`
- `nozzle_diameter = 0.4`
- `nozzle_high_flow = 1`

### Original Prusa XL - 5T Input Shaper 0.4 nozzle

- `printer_model = XL5IS`
- `printer_variant = 0.4`
- `nozzle_diameter = 0.4,0.4,0.4,0.4,0.4`

No filament, temperature, layer-height, infill, or other rejection rules are invented here.
Those fields may be displayed, but they are not compatibility gates unless you add a real project requirement for them.

## Stage 1 - file format

The validator accepts only `.gcode` and `.bgcode`.

- `.bgcode`: content must start with Prusa BGCODE `GCDE` magic bytes.
- `.gcode`: content must be UTF-8 text, not contain NUL/binary data, and contain a recognizable `G...`, `M...`, or `T...` command.
- An extension/content mismatch is rejected.

This means renaming an image/PDF/text file to `.gcode` or `.bgcode` does not bypass validation.

## Stage 2 - parse/integrity

For `.bgcode`, the implementation parses its block structure and checks CRC32 when present.
For `.gcode`, it verifies there are executable G/M/T commands and parses Prusa-style comment metadata.

## Stage 3 - metadata

Required compatibility metadata:

- `printer_model`
- `printer_variant`
- `nozzle_diameter`

CORE One HF0.4 additionally requires `nozzle_high_flow = 1` when comparing that profile.

For text `.gcode`, metadata is processed in file order. If a key appears again near the bottom, the bottom value wins.

## Stage 4 - BOTH printer checks

The response always contains both checks after stages 1-3 pass:

```json
{
  "printer_checks": {
    "core_one_hf04": {"result": "MATCH or NO_MATCH"},
    "xl_5t_is_04": {"result": "MATCH or NO_MATCH"}
  }
}
```

## Stage 5 - workflow decision

PASS:

```json
{
  "status": "PASS",
  "next_step": "SELECT_PRINTER"
}
```

The frontend should display/filter only physical printers belonging to `compatible_profile`.
Validation does **not** queue or start a print.

FAIL:

```json
{
  "status": "FAIL",
  "next_step": "UPLOAD_GCODE"
}
```

Show `message`, `errors`, `failed_stage`, and (when stage 4 ran) the two `printer_checks` to the user.

## Run from command line

```bash
python gcode_validator.py your_file.bgcode
```

## FastAPI

```bash
pip install -r requirements.txt
uvicorn app_example:app --reload
```

Endpoint:

```text
POST /api/gcode/validate
multipart/form-data: file=<uploaded file>
```

## Tests

```bash
pytest -q
```

The tests include the uploaded CORE One sample, bad format, extension/content mismatch, corrupted BGCODE, text CORE One, text XL 5T, missing metadata, and a valid file that matches neither printer.

## Verification basis

- Prusa `libbgcode` defines binary G-code as a block format with metadata/G-code blocks and checksum support.
- The included real uploaded sample is used to test the CORE One path.
- The XL test is a metadata fixture for the explicit XL profile check; it is not represented as a real uploaded XL BGCODE sample.
