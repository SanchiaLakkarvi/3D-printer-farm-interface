# Decision log

## 2026-08-17 — Separate hardware, slicer, and transport identities

**Decision:** Keep `physical_model`, `gcode_printer_model`, and
`sdk_identity` as separate fields.

**Reason:** UWA's logical inventory names are not the values emitted by
PrusaSlicer, while the legacy Python SDK has no XL or CORE One printer enum.
Conflating the three identities either rejects valid files or invents an SDK
identity that is not supported upstream.

## 2026-08-17 — Treat Binary G-code as a first-class input

**Decision:** Detect Binary G-code by its `GCDE` signature and use the official
`libbgcode`/`pybgcode` implementation to decode it. Keep the existing ASCII
parser as a second input adapter.

**Reason:** Both confirmed PrusaSlicer printer profiles enable Binary G-code by
default. Parsing arbitrary binary bytes as a UTF-8 footer is incorrect, and a
local partial implementation of the compression/checksum format would be a
maintenance and safety risk.

## 2026-08-17 — Keep the legacy SDK transport mock-only

**Decision:** Introduce a transport interface around the current
`Prusa-Connect-SDK-Printer` integration, but do not fabricate a physical Buddy
WebSocket adapter before UWA confirms firmware and connection mode.

**Reason:** Current Buddy firmware communication differs from the legacy
polling SDK and the SDK does not model XL or CORE One. Implementing an assumed
wire protocol would create false compatibility. The simulator, validation, and
accounting layers remain usable while a real adapter is acceptance-tested
against UWA hardware.

## 2026-08-17 — Validate commands as well as metadata

**Decision:** Decode commands and validate firmware compatibility commands,
tool references, motion bounds, and temperature ceilings in addition to slicer
metadata.

**Reason:** PrusaSlicer footer metadata is editable text and cannot by itself
protect a physical printer. The configured ceilings use published hardware
limits; narrower UWA policy limits can be added without changing the parser.
