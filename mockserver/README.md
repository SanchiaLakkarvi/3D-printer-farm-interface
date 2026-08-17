# Prusa Farm Mock Printer (FastAPI + Prusa Connect SDK Printer)

This project simulates **multiple printer-side clients** while using the required
`prusa3d/Prusa-Connect-SDK-Printer` library. It is designed so the production
backend behaves like a Connect-compatible control plane instead of calling a
mock-only `POST /print` endpoint.

## Architectural decision

For a mock that will later be replaced by a physical Prusa printer, use this
boundary:

```text
Student/UI
    |
    | upload G-code / choose printer
    v
UWA Backend = Connect-compatible server + validation + queue + accounting
    ^
    |  POST /p/telemetry      (printer -> backend)
    |  POST /p/events         (printer -> backend)
    |  GET  /p/teams/{team_id}/files/{hash}/raw
    |
Mock Printer today (this project)
Physical XL / CORE One later
```

The FastAPI endpoints in this project under `/control/*` are **operator/test
controls only**. The backend must not depend on them for normal printing.
Printing commands come back in the backend's HTTP response to printer
telemetry, as required by the Python SDK.

## Supported UWA hardware profiles

The simulator targets these two UWA printer configurations:

| Domain model | PrusaSlicer `printer_model` | Required printer preset | Tool configuration |
| --- | --- | --- | --- |
| `PRUSA_XL_5T_INPUT_SHAPER` | `XL5IS` | `Original Prusa XL - 5T Input Shaper 0.4 nozzle` | Five standard-flow 0.4 mm toolheads |
| `PRUSA_CORE_ONE` | `COREONE` | `Prusa CORE One HF0.4 nozzle` | One high-flow 0.4 mm toolhead |

The XL build volume is 360 x 360 x 360 mm. The CORE One build volume is
250 x 220 x 270 mm and includes a chamber. These hardware facts are distinct
from UWA policy such as allowed filament, temperature, print, and filament
presets; policy values must be populated from UWA-approved exports.

## Transport compatibility warning

The current `Prusa-Connect-SDK-Printer` source does **not** define XL or CORE One
inside `const.PrinterType`. Therefore this simulator keeps two identities
separate:

- `physical_model`: the application's logical hardware model.
- `gcode_printer_model`: the exact PrusaSlicer metadata identity (`XL5IS` or
  `COREONE`) used by validation.
- `sdk_identity`: a clearly synthetic transport identity used only to satisfy
  the current Python SDK object shape in the mock.

Do not invent numeric XL/CORE One SDK enum values. When the UWA printers are
available, capture the real registration/headers and implement a dedicated
real-printer protocol adapter.

The included legacy SDK transport is mock-only. Current Buddy firmware uses a
newer Connect communication mechanism than the SDK's HTTP polling protocol.
The project therefore keeps transport behind an interface and does not claim
that `/p/telemetry` is the current physical-printer protocol. A physical
adapter must be selected after UWA confirms the installed firmware and whether
the integration is Prusa Connect or local PrusaLink. See
`docs/decision-log.md`.

## G-code validation

Validation is **profile-driven** and supports both ASCII G-code and Prusa
Binary G-code. Format detection uses the file signature rather than the file
extension:

- Binary G-code starts with `GCDE`; its metadata and commands are decoded with
  the official `libbgcode`/`pybgcode` implementation pinned from Prusa's source
  repository (the binding is not published on PyPI).
- ASCII G-code metadata is read from PrusaSlicer-style assignments:

```text
; key = value
```

It deliberately does not hard-code an assumed UWA XL/CORE One profile. Each
approved profile declares the exact metadata keys and accepted values.

Supported validation operators:

- `present`
- `equals`
- `one_of`
- `numeric_range`
- `sequence_equals`

Dynamic expected values can come from the selected printer and toolheads:

- `gcode_printer_model`
- `tool_materials`
- `nozzle_diameters`
- `nozzle_high_flow`

Required hardware checks include printer metadata, build volume, the exact
printer preset, nozzle diameter/count/type, and Input Shaper compatibility
commands. UWA policy profiles may additionally constrain print/filament preset,
material, temperatures, infill, layer/extrusion settings, duration, and
filament use. XL consumables are tracked per toolhead. Colour is tracked on the
spool but is not required to match G-code.

Metadata comments alone are not a safety boundary because they can be edited.
Validation also inspects decoded commands for printer/nozzle/Input Shaper
compatibility, tool references, motion bounds, and configured temperature
limits. For the strongest trust boundary, production should slice uploaded
models with a pinned UWA profile instead of accepting arbitrary user-generated
G-code.

### Where validation belongs

Production should validate **before** the backend makes a file available to a
printer. The mock additionally validates the downloaded file locally. This is
intentional defense-in-depth for testing, but the physical printer must not be
the only validation boundary.

## Prusa flow implemented

The SDK-side worker supports:

```text
READY
  |
  | backend returns START_CONNECT_DOWNLOAD from POST /p/telemetry
  v
DOWNLOAD
  |
  | printer GET /p/teams/{team_id}/files/{hash}/raw
  | local G-code validation
  v
READY
  |
  | backend returns START_PRINT
  v
PRINTING <-> PAUSED
  |
  +---- STOP_PRINT ----> STOPPED
  |
  `---- 100% ----------> FINISHED
```

If `START_CONNECT_DOWNLOAD.kwargs.printing` is `true`, the simulator also
supports starting automatically after a successful validated download.

The SDK itself reports transfer information/events and this project sends
telemetry every second. Operator status exposes five independent XL toolheads,
the active tool, per-tool spool remainder, and the CORE One chamber. Preheating
does not advance print progress, and filament is deducted only after a completed
print. Print duration comes from the G-code metric configured by the approved
profile. `simulation_speed=1` means wall-clock speed; larger values accelerate
test runs.

## Backend contract needed by the mock

Your backend needs at least:

### `POST /p/telemetry`

No pending command:

```http
HTTP/1.1 204 No Content
```

Send Connect download:

```http
HTTP/1.1 200 OK
Command-Id: 101
Content-Type: application/json

{
  "command": "START_CONNECT_DOWNLOAD",
  "kwargs": {
    "path": "/usb/job-123.gcode",
    "team_id": 7,
    "hash": "abc123",
    "printing": false
  }
}
```

Later start the validated file:

```http
HTTP/1.1 200 OK
Command-Id: 102
Content-Type: application/json

{
  "command": "START_PRINT",
  "args": ["/usb/job-123.gcode"]
}
```

Pause/resume/stop use the SDK command names `PAUSE_PRINT`, `RESUME_PRINT`, and
`STOP_PRINT`.

### `POST /p/events`

Accept printer events and normally answer `204 No Content`. Important events
include command `ACCEPTED`/`FINISHED`, `STATE_CHANGED`, and transfer events.
The simulator also sends a `FAILED` event when its defense-in-depth validation
rejects downloaded G-code.

### `GET /p/teams/{team_id}/files/{hash}/raw`

Return the exact raw G-code bytes with HTTP 200 and a supported G-code MIME
type. The backend should only expose a job here after server-side validation
has passed for the selected printer/profile.

## Configuration

`config/printers.yaml` contains runnable mock instances with the confirmed UWA
hardware identities. Its serials, credentials, spool values, and process policy
are synthetic.

`config/uwa-printers.template.yaml` contains the confirmed hardware profiles and
keeps printers disabled until inventory credentials and UWA policy are added.
Populate it from:

1. actual UWA printer serial/registration details and installed firmware,
2. currently loaded material/spool per XL toolhead,
3. approved print and filament preset IDs,
4. one exported BGCode file per permitted combination.

Do not enable a production profile until these values are known.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`pybgcode` is compiled from Prusa's pinned source commit, so local Linux builds
need Git, a C/C++ build toolchain, and CMake. The Dockerfile installs them.

Run the optional development Connect stub in terminal 1:

```bash
uvicorn examples.connect_stub:app --host 127.0.0.1 --port 9000
```

Run the multi-printer simulator in terminal 2:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8080
```

Open the FastAPI operator API at `/docs` on port 8080.

## End-to-end demo

Upload the included synthetic valid XL-like file to the development Connect
stub:

```bash
curl -X PUT \
  --data-binary @tests/data-valid-xl.gcode \
  http://127.0.0.1:9000/dev/files/7/abc123
```

Queue `START_CONNECT_DOWNLOAD` for `mock-xl-01` using its configured
fingerprint:

```bash
curl -X POST http://127.0.0.1:9000/dev/printers/mock-xl-0001-fingerprint/commands \
  -H 'Content-Type: application/json' \
  -d '{
    "command":"START_CONNECT_DOWNLOAD",
    "kwargs":{
      "path":"/usb/job-123.gcode",
      "team_id":7,
      "hash":"abc123",
      "printing":false
    }
  }'
```

After download/validation, queue print:

```bash
curl -X POST http://127.0.0.1:9000/dev/printers/mock-xl-0001-fingerprint/commands \
  -H 'Content-Type: application/json' \
  -d '{"command":"START_PRINT","args":["/usb/job-123.gcode"]}'
```

Inspect simulator status:

```bash
curl http://127.0.0.1:8080/control/printers/mock-xl-01
```

Inspect what a backend receives:

```bash
curl http://127.0.0.1:9000/dev/events
curl http://127.0.0.1:9000/dev/telemetry
```

## Operator/test FastAPI endpoints

- `GET /health`
- `GET /control/printers`
- `GET /control/printers/{printer_id}`
- `POST /control/printers/{printer_id}/validate?virtual_path=/usb/file.gcode`
- `POST /control/printers/{printer_id}/fault`
- `POST /control/printers/{printer_id}/reset`
- `PATCH /control/printers/{printer_id}/consumables`

Again: these are not the production printing API.

Consumables are addressed per physical tool slot, for example:

```json
{"slot": 2, "material": "PLA", "colour": "orange", "remaining_g": 750}
```

## Tests

```bash
pytest -q
```

Tests cover valid ASCII and Binary G-code, both confirmed hardware profiles,
high-flow/tool compatibility, command safety limits, hardware config invariants,
multi-tool simulator state, and incompatible-printer rejection.

## What the team still needs from UWA

No software design can safely infer these values. Obtain:

- installed firmware version and connection mode for each printer;
- approved material list and spool density data;
- the approved PrusaSlicer print and filament profile IDs;
- a real BGCode generated by each approved profile for contract fixtures;
- temperature/infill/layer/extrusion values or ranges the lab approves.

These remaining values are policy and deployment inputs. The parser and
simulator already model Binary G-code, the XL five-tool layout, and CORE One's
high-flow nozzle/chamber; the physical transport still requires acceptance
testing with the installed UWA firmware.
