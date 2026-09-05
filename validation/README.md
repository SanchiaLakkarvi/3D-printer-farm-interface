# G-code validation for two supported Prusa printers

This package implements the approved validation flow for **one uploaded G-code file**.
The same uploaded file is checked against **both supported printer profiles together**.

```text
Upload G-code file
    |
    v
1. FILE FORMAT VALIDATION
    |
    +-- INVALID --> FAIL immediately
    |
    v
2. Parse G-code + integrity check
    |
    +-- Cannot parse / corrupted --> FAIL
    |
    v
3. Read bottom / printer metadata
    |
    v
4. Check the SAME G-code against BOTH printers
    |
    +--> Prusa CORE One HF0.4 nozzle
    |
    +--> Original Prusa XL - 5T Input Shaper 0.4 nozzle
    |
    v
5. Does one supported printer match?
   YES --> PASS --> SELECT_PRINTER
   NO  --> FAIL --> UPLOAD_GCODE / re-slice
```

## Supported printer profiles

### Prusa CORE One HF0.4 nozzle

Compatibility fields:

- `printer_model = COREONE`
- `printer_variant = HF0.4`
- `nozzle_diameter = 0.4`
- `nozzle_high_flow = 1`

### Original Prusa XL - 5T Input Shaper 0.4 nozzle

Compatibility fields:

- `printer_model = XL5IS`
- `printer_variant = 0.4`
- `nozzle_diameter = 0.4,0.4,0.4,0.4,0.4`

No extra rejection rules for filament, temperatures, layer height, infill, or supports are added.
Those values can be displayed, but they are not compatibility gates unless your project requirements define them later.

## Stage 1 — validate G-code file format

The validator does not trust the filename alone.
It checks the actual file content first.

- Text G-code must be readable text and contain recognizable `G...`, `M...`, or `T...` commands.
- The supplied Prusa sample uses a binary representation of G-code, so its actual binary header is checked before parsing.
- A JPG, PDF, random text file, or other invalid content renamed to a G-code filename will fail here.

Public API results always report the file format as:

```json
{
  "format": "GCODE"
}
```

## Stage 2 — parse and integrity check

The validator parses the G-code according to how it is stored.
For the supplied Prusa sample, block boundaries and CRC32 checksums are verified.
For text G-code, executable commands and metadata comments are parsed.

If parsing fails or the file is corrupted:

```json
{
  "status": "FAIL",
  "failed_stage": 2,
  "message": "G-code could not be parsed or failed integrity validation.",
  "next_step": "UPLOAD_GCODE"
}
```

## Stage 3 — read metadata

The validator reads the printer metadata needed for compatibility:

- `printer_model`
- `printer_variant`
- `nozzle_diameter`
- `nozzle_high_flow` when required by the CORE One HF0.4 profile

For text G-code, metadata is processed in file order, so a repeated value near the bottom overrides an earlier value.

## Stage 4 — compare against both printers

After stages 1–3 pass, the validator **always checks both profiles**:

```json
{
  "printer_checks": {
    "core_one_hf04": {
      "result": "MATCH or NO_MATCH"
    },
    "xl_5t_is_04": {
      "result": "MATCH or NO_MATCH"
    }
  }
}
```

## Stage 5 — workflow decision

If one supported printer matches:

```json
{
  "status": "PASS",
  "format": "GCODE",
  "next_step": "SELECT_PRINTER"
}
```

The frontend should show/filter only physical printers belonging to the matched profile.
Validation does **not** queue or start the print.

If neither printer matches:

```json
{
  "status": "FAIL",
  "failed_stage": 5,
  "message": "G-code is valid, but it is not compatible with either supported printer.",
  "next_step": "UPLOAD_GCODE"
}
```

## Run from command line

```bash
python gcode_validator.py <gcode-file>
```

## Run tests

```bash
pytest -q
```

The tests cover:

- the real uploaded CORE One sample;
- CORE One matching and XL non-matching for that same file;
- an XL 5T fixture matching XL and not CORE One;
- wrong file format;
- filename/content mismatch;
- corrupted G-code;
- missing printer metadata;
- valid G-code that matches neither supported printer.
