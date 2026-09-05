from __future__ import annotations

import json
import re
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Supported upload formats
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".gcode", ".bgcode"}
BINARY_GCODE_MAGIC = b"GCDE"
BINARY_GCODE_VERSION = 1
CHECKSUM_NONE = 0
CHECKSUM_CRC32 = 1

# Binary G-code block types used by the uploaded Prusa G-code file.
FILE_METADATA = 0
GCODE_BLOCK = 1
SLICER_METADATA = 2
PRINTER_METADATA = 3
PRINT_METADATA = 4
THUMBNAIL = 5

# Parameter bytes following each binary G-code block header.
BLOCK_PARAM_SIZE = {
    FILE_METADATA: 2,
    GCODE_BLOCK: 2,
    SLICER_METADATA: 2,
    PRINTER_METADATA: 2,
    PRINT_METADATA: 2,
    THUMBNAIL: 6,
}

# ONE uploaded file is compared against BOTH profiles.
# These are the only printer compatibility rules in this implementation.
SUPPORTED_PROFILES: dict[str, dict[str, Any]] = {
    "core_one_hf04": {
        "display_name": "Prusa CORE One HF0.4 nozzle",
        "printer_model": "COREONE",
        "printer_variant": "HF0.4",
        "nozzle_diameter": [0.4],
        "nozzle_high_flow": [1],
    },
    "xl_5t_is_04": {
        "display_name": "Original Prusa XL - 5T Input Shaper 0.4 nozzle",
        "printer_model": "XL5IS",
        "printer_variant": "0.4",
        "nozzle_diameter": [0.4, 0.4, 0.4, 0.4, 0.4],
        # Standard 0.4 profile: do not require a high-flow flag.
        "nozzle_high_flow": None,
    },
}


class ValidationError(ValueError):
    """Raised for a validation-stage failure."""


class BinaryGCodeParseError(ValidationError):
    pass


class TextGCodeParseError(ValidationError):
    pass


@dataclass
class FormatResult:
    kind: str  # "BINARY" or "TEXT"; public format is always GCODE
    extension: str


@dataclass
class BinaryGCodeBlock:
    block_type: int
    compression: int
    uncompressed_size: int
    compressed_size: int
    params: bytes
    payload: bytes
    crc_ok: bool


@dataclass
class ParsedGCode:
    kind: str
    file_metadata: dict[str, str]
    printer_metadata: dict[str, str]
    print_metadata: dict[str, str]
    slicer_metadata: dict[str, str]
    gcode_blocks: int
    integrity_ok: bool


# ---------------------------------------------------------------------------
# Stage 1: file format validation
# ---------------------------------------------------------------------------
_GCODE_COMMAND_RE = re.compile(
    rb"(?m)^\s*(?:N\d+\s+)?(?:G\d+(?:\.\d+)?|M\d+(?:\.\d+)?|T\d+)\b"
)


def validate_file_format(path: str | Path) -> FormatResult:
    """
    Validate the file format BEFORE parsing metadata or checking printers.

    Rules:
      * accept the normal .gcode extension and the extension used by the supplied Prusa G-code sample;
      * files using the uploaded sample's binary G-code extension must contain the expected G-code header bytes;
      * .gcode must be text-like and contain at least one G/M/T command;
      * extension/content mismatch is rejected.

    Renaming a JPG/PDF/TXT to a G-code extension therefore does not pass.
    """
    path = Path(path)

    if not path.is_file():
        raise ValidationError("Uploaded file does not exist or is not a regular file.")
    if path.stat().st_size == 0:
        raise ValidationError("Uploaded file is empty.")

    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension {ext or '<none>'!r}. "
            "Only .gcode and .bgcode are accepted."
        )

    with path.open("rb") as f:
        sample = f.read(256 * 1024)

    is_binary_gcode = sample.startswith(BINARY_GCODE_MAGIC)

    if ext == ".bgcode":
        if not is_binary_gcode:
            raise ValidationError(
                "The uploaded file is not a valid G-code file (invalid binary header)."
            )
        return FormatResult(kind="BINARY", extension=ext)

    # ext == .gcode
    if is_binary_gcode:
        raise ValidationError(
            "The uploaded file extension does not match its G-code content."
        )

    if b"\x00" in sample:
        raise ValidationError("The .gcode file contains binary/NUL data and is not valid text G-code.")

    try:
        sample.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValidationError("The .gcode file is not valid UTF-8 text G-code.") from exc

    if not _GCODE_COMMAND_RE.search(sample):
        raise ValidationError(
            "The .gcode file does not contain a recognizable G-code command (G..., M..., or T...)."
        )

    return FormatResult(kind="TEXT", extension=ext)


# ---------------------------------------------------------------------------
# Stage 2: parse G-code and validate integrity
# ---------------------------------------------------------------------------
def _parse_key_values(raw: bytes) -> dict[str, str]:
    text = raw.decode("utf-8", errors="strict")
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def _decode_metadata_block(block: BinaryGCodeBlock) -> dict[str, str]:
    if len(block.params) < 2:
        raise BinaryGCodeParseError("Metadata block is missing its encoding parameter.")

    metadata_encoding = struct.unpack("<H", block.params[:2])[0]
    if metadata_encoding != 0:
        raise BinaryGCodeParseError(
            f"Unsupported G-code metadata encoding {metadata_encoding}; expected INI encoding 0."
        )

    if block.compression == 0:
        raw = block.payload
    elif block.compression == 1:
        try:
            raw = zlib.decompress(block.payload)
        except zlib.error as exc:
            raise BinaryGCodeParseError(f"Cannot decompress G-code metadata block: {exc}") from exc
    else:
        raise BinaryGCodeParseError(
            "This validator cannot decode metadata using G-code binary "
            f"compression type {block.compression}."
        )

    if len(raw) != block.uncompressed_size:
        raise BinaryGCodeParseError(
            "G-code metadata size mismatch: "
            f"expected {block.uncompressed_size}, got {len(raw)}."
        )

    return _parse_key_values(raw)


def parse_binary_gcode(path: str | Path) -> ParsedGCode:
    """Parse binary G-code structure, verify block CRC32 values, and read metadata."""
    path = Path(path)
    data = path.read_bytes()

    # Header: uint32 magic + uint32 version + uint16 checksum type.
    if len(data) < 10:
        raise BinaryGCodeParseError("G-code binary header is truncated.")

    magic, version, checksum_type = struct.unpack_from("<IIH", data, 0)
    if magic.to_bytes(4, "little") != BINARY_GCODE_MAGIC:
        raise BinaryGCodeParseError("Invalid G-code binary header.")
    if version != BINARY_GCODE_VERSION:
        raise BinaryGCodeParseError(
            f"Unsupported G-code binary version {version}; this validator supports version {BINARY_GCODE_VERSION}."
        )
    if checksum_type not in (CHECKSUM_NONE, CHECKSUM_CRC32):
        raise BinaryGCodeParseError(f"Unsupported G-code checksum type {checksum_type}.")

    offset = 10
    blocks: list[BinaryGCodeBlock] = []

    while offset < len(data):
        block_start = offset
        if offset + 8 > len(data):
            raise BinaryGCodeParseError("Truncated G-code block header.")

        block_type, compression, uncompressed_size = struct.unpack_from("<HHI", data, offset)
        offset += 8

        if block_type not in BLOCK_PARAM_SIZE:
            raise BinaryGCodeParseError(f"Unsupported/invalid G-code block type {block_type}.")
        if compression not in (0, 1, 2, 3):
            raise BinaryGCodeParseError(f"Unsupported/invalid G-code compression type {compression}.")

        if compression == 0:
            compressed_size = uncompressed_size
        else:
            if offset + 4 > len(data):
                raise BinaryGCodeParseError("Truncated compressed G-code block header.")
            compressed_size = struct.unpack_from("<I", data, offset)[0]
            offset += 4

        param_size = BLOCK_PARAM_SIZE[block_type]
        if offset + param_size + compressed_size > len(data):
            raise BinaryGCodeParseError("Truncated G-code block payload.")

        params = data[offset : offset + param_size]
        offset += param_size
        payload = data[offset : offset + compressed_size]
        offset += compressed_size

        crc_ok = True
        if checksum_type == CHECKSUM_CRC32:
            if offset + 4 > len(data):
                raise BinaryGCodeParseError("G-code block is missing its CRC32 checksum.")
            stored_crc = struct.unpack_from("<I", data, offset)[0]
            calculated_crc = zlib.crc32(data[block_start:offset]) & 0xFFFFFFFF
            crc_ok = stored_crc == calculated_crc
            offset += 4

        blocks.append(
            BinaryGCodeBlock(
                block_type=block_type,
                compression=compression,
                uncompressed_size=uncompressed_size,
                compressed_size=compressed_size,
                params=params,
                payload=payload,
                crc_ok=crc_ok,
            )
        )

    if not blocks:
        raise BinaryGCodeParseError("G-code file contains no data blocks.")

    if not all(block.crc_ok for block in blocks):
        raise BinaryGCodeParseError(
            "CRC32 verification failed. The G-code file is corrupted or was modified."
        )

    file_meta: dict[str, str] = {}
    printer_meta: dict[str, str] = {}
    print_meta: dict[str, str] = {}
    slicer_meta: dict[str, str] = {}
    gcode_blocks = 0

    for block in blocks:
        if block.block_type == FILE_METADATA:
            file_meta.update(_decode_metadata_block(block))
        elif block.block_type == PRINTER_METADATA:
            printer_meta.update(_decode_metadata_block(block))
        elif block.block_type == PRINT_METADATA:
            print_meta.update(_decode_metadata_block(block))
        elif block.block_type == SLICER_METADATA:
            slicer_meta.update(_decode_metadata_block(block))
        elif block.block_type == GCODE_BLOCK:
            gcode_blocks += 1

    if gcode_blocks == 0:
        raise BinaryGCodeParseError("G-code file contains no executable G-code data blocks.")

    return ParsedGCode(
        kind="BINARY",
        file_metadata=file_meta,
        printer_metadata=printer_meta,
        print_metadata=print_meta,
        slicer_metadata=slicer_meta,
        gcode_blocks=gcode_blocks,
        integrity_ok=True,
    )


_COMMENT_KV_RE = re.compile(r"^\s*;\s*([^=]+?)\s*=\s*(.*?)\s*$")


def parse_text_gcode(path: str | Path) -> ParsedGCode:
    """
    Parse ASCII Prusa-style G-code.

    Metadata comments are read in file order, so metadata written near the bottom
    naturally overrides an earlier duplicate key. This matches the user's request
    to treat the bottom metadata as the main source for compatibility checking.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TextGCodeParseError("Cannot decode .gcode as UTF-8 text.") from exc

    metadata: dict[str, str] = {}
    command_count = 0

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith(";"):
            match = _COMMENT_KV_RE.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip().strip('"')
                metadata[key] = value
            continue

        # Remove inline comment before checking the command token.
        command_part = stripped.split(";", 1)[0].strip()
        if re.match(r"^(?:N\d+\s+)?(?:G\d+(?:\.\d+)?|M\d+(?:\.\d+)?|T\d+)\b", command_part):
            command_count += 1

    if command_count == 0:
        raise TextGCodeParseError("No executable G/M/T G-code commands were found.")

    # Prusa text G-code stores the configuration as comment key/value data rather
    # than binary G-code's separate metadata blocks. Keep one metadata dictionary available
    # through the same normalized interface.
    return ParsedGCode(
        kind="TEXT",
        file_metadata=metadata,
        printer_metadata=metadata,
        print_metadata=metadata,
        slicer_metadata=metadata,
        gcode_blocks=command_count,
        integrity_ok=True,
    )


def parse_gcode(path: str | Path, fmt: FormatResult) -> ParsedGCode:
    if fmt.kind == "BINARY":
        return parse_binary_gcode(path)
    if fmt.kind == "TEXT":
        return parse_text_gcode(path)
    raise ValidationError(f"Unsupported detected format {fmt.kind!r}.")


# ---------------------------------------------------------------------------
# Stage 3: read/normalize metadata used for printer matching
# ---------------------------------------------------------------------------
def _first_value(parsed: ParsedGCode, *keys: str) -> str | None:
    # Prefer printer metadata, then slicer, print, file metadata.
    for mapping in (
        parsed.printer_metadata,
        parsed.slicer_metadata,
        parsed.print_metadata,
        parsed.file_metadata,
    ):
        for key in keys:
            value = mapping.get(key)
            if value not in (None, ""):
                return value
    return None


def extract_metadata(parsed: ParsedGCode) -> dict[str, str | None]:
    detected = {
        "producer": _first_value(parsed, "Producer", "producer"),
        "printer_model": _first_value(parsed, "printer_model"),
        "printer_variant": _first_value(parsed, "printer_variant"),
        "printer_settings_id": _first_value(parsed, "printer_settings_id"),
        "nozzle_diameter": _first_value(parsed, "nozzle_diameter"),
        "nozzle_high_flow": _first_value(parsed, "nozzle_high_flow"),
        "filament_type": _first_value(parsed, "filament_type"),
        "layer_height": _first_value(parsed, "layer_height"),
        "estimated_print_time": _first_value(
            parsed,
            "estimated printing time (normal mode)",
            "estimated printing time",
        ),
        "filament_used_g": _first_value(
            parsed,
            "total filament used [g]",
            "filament used [g]",
        ),
    }

    # These fields are the minimum required for BOTH configured printer checks.
    required = ("printer_model", "printer_variant", "nozzle_diameter")
    missing = [key for key in required if not detected.get(key)]
    if missing:
        raise ValidationError(
            "Required printer metadata is missing: " + ", ".join(missing) + "."
        )

    return detected


# ---------------------------------------------------------------------------
# Stage 4: check the SAME upload against BOTH printer profiles
# ---------------------------------------------------------------------------
def _csv_floats(value: str | None) -> list[float]:
    if not value:
        return []
    try:
        return [float(part.strip()) for part in value.split(",")]
    except ValueError:
        return []


def _csv_ints(value: str | None) -> list[int]:
    if not value:
        return []
    try:
        return [int(float(part.strip())) for part in value.split(",")]
    except ValueError:
        return []


def _same_floats(actual: list[float], expected: list[float]) -> bool:
    return len(actual) == len(expected) and all(
        abs(a - b) <= 1e-6 for a, b in zip(actual, expected)
    )


def _match_profile(metadata: dict[str, str | None], profile_id: str) -> tuple[bool, list[str]]:
    expected = SUPPORTED_PROFILES[profile_id]
    model = metadata.get("printer_model")
    variant = metadata.get("printer_variant")
    nozzles = _csv_floats(metadata.get("nozzle_diameter"))
    high_flow = _csv_ints(metadata.get("nozzle_high_flow"))

    reasons: list[str] = []

    if model != expected["printer_model"]:
        reasons.append(f"printer_model={model!r}; expected {expected['printer_model']!r}")

    if variant != expected["printer_variant"]:
        reasons.append(f"printer_variant={variant!r}; expected {expected['printer_variant']!r}")

    if not _same_floats(nozzles, expected["nozzle_diameter"]):
        reasons.append(
            f"nozzle_diameter={nozzles}; expected {expected['nozzle_diameter']}"
        )

    expected_hf = expected["nozzle_high_flow"]
    if expected_hf is not None and high_flow != expected_hf:
        reasons.append(f"nozzle_high_flow={high_flow}; expected {expected_hf}")

    return not reasons, reasons


def check_both_printers(
    metadata: dict[str, str | None],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    checks: dict[str, dict[str, Any]] = {}
    matches: list[str] = []

    # Always evaluate BOTH profiles when stages 1-3 pass.
    for profile_id, profile in SUPPORTED_PROFILES.items():
        matched, reasons = _match_profile(metadata, profile_id)
        checks[profile_id] = {
            "printer": profile["display_name"],
            "matched": matched,
            "result": "MATCH" if matched else "NO_MATCH",
            "reasons": reasons,
        }
        if matched:
            matches.append(profile_id)

    return checks, matches


def _not_checked_printers(reason: str) -> dict[str, dict[str, Any]]:
    return {
        profile_id: {
            "printer": profile["display_name"],
            "matched": False,
            "result": "NOT_CHECKED",
            "reasons": [reason],
        }
        for profile_id, profile in SUPPORTED_PROFILES.items()
    }


def _stage(number: int, name: str, status: str, **details: Any) -> dict[str, Any]:
    result = {"stage": number, "name": name, "status": status}
    if details:
        result["details"] = details
    return result


# ---------------------------------------------------------------------------
# Stages 1 -> 5 combined
# ---------------------------------------------------------------------------
def validate_upload(path: str | Path) -> dict[str, Any]:
    """
    Required flow:

      1. FILE FORMAT VALIDATION
      2. Parse G-code + integrity
      3. Read metadata
      4. Check against BOTH printers
      5. Exactly one supported printer matches -> PASS

    PASS moves only to SELECT_PRINTER. It does not queue/start a print.
    """
    path = Path(path)
    stages: list[dict[str, Any]] = []

    # Stage 1 ---------------------------------------------------------------
    try:
        fmt = validate_file_format(path)
    except (OSError, ValidationError) as exc:
        stages.append(_stage(1, "FILE_FORMAT_VALIDATION", "FAIL", reason=str(exc)))
        return {
            "status": "FAIL",
            "passed": False,
            "failed_stage": 1,
            "file": path.name,
            "message": "Invalid G-code file format.",
            "errors": [str(exc)],
            "validation_stages": stages,
            "printer_checks": _not_checked_printers(
                "Not checked because file format validation failed."
            ),
            "compatible_profiles": [],
            "compatible_printers": [],
            "next_step": "UPLOAD_GCODE",
        }

    stages.append(
        _stage(
            1,
            "FILE_FORMAT_VALIDATION",
            "PASS",
            detected_format="GCODE",
            extension=fmt.extension,
        )
    )

    # Stage 2 ---------------------------------------------------------------
    try:
        parsed = parse_gcode(path, fmt)
    except (OSError, UnicodeDecodeError, ValidationError) as exc:
        stages.append(_stage(2, "PARSE_AND_INTEGRITY", "FAIL", reason=str(exc)))
        return {
            "status": "FAIL",
            "passed": False,
            "failed_stage": 2,
            "file": path.name,
            "format": "GCODE",
            "message": "G-code could not be parsed or failed integrity validation.",
            "errors": [str(exc)],
            "validation_stages": stages,
            "printer_checks": _not_checked_printers(
                "Not checked because parsing/integrity validation failed."
            ),
            "compatible_profiles": [],
            "compatible_printers": [],
            "next_step": "UPLOAD_GCODE",
        }

    stages.append(
        _stage(
            2,
            "PARSE_AND_INTEGRITY",
            "PASS",
            parsed_format="GCODE",
            gcode_blocks_or_commands=parsed.gcode_blocks,
            integrity_ok=parsed.integrity_ok,
        )
    )

    # Stage 3 ---------------------------------------------------------------
    try:
        metadata = extract_metadata(parsed)
    except ValidationError as exc:
        stages.append(_stage(3, "READ_METADATA", "FAIL", reason=str(exc)))
        return {
            "status": "FAIL",
            "passed": False,
            "failed_stage": 3,
            "file": path.name,
            "format": "GCODE",
            "message": "Required printer metadata could not be read.",
            "errors": [str(exc)],
            "validation_stages": stages,
            "printer_checks": _not_checked_printers(
                "Not checked because required printer metadata is missing."
            ),
            "compatible_profiles": [],
            "compatible_printers": [],
            "next_step": "UPLOAD_GCODE",
        }

    stages.append(
        _stage(
            3,
            "READ_METADATA",
            "PASS",
            printer_model=metadata.get("printer_model"),
            printer_variant=metadata.get("printer_variant"),
            nozzle_diameter=metadata.get("nozzle_diameter"),
            nozzle_high_flow=metadata.get("nozzle_high_flow"),
        )
    )

    # Stage 4 ---------------------------------------------------------------
    printer_checks, matches = check_both_printers(metadata)
    stages.append(
        _stage(
            4,
            "CHECK_BOTH_PRINTERS",
            "PASS",
            printers_checked=list(SUPPORTED_PROFILES.keys()),
            matching_profiles=matches,
        )
    )

    # Stage 5 ---------------------------------------------------------------
    # With these non-overlapping profiles, one exact match is the expected PASS.
    if len(matches) == 0:
        stages.append(
            _stage(
                5,
                "SUPPORTED_PRINTER_MATCH",
                "FAIL",
                reason="Neither supported printer profile matched.",
            )
        )
        return {
            "status": "FAIL",
            "passed": False,
            "failed_stage": 5,
            "file": path.name,
            "format": "GCODE",
            "message": (
                "G-code is valid, but it is not compatible with either supported printer. "
                "Re-slice it for CORE One HF0.4 or XL 5T Input Shaper 0.4."
            ),
            "errors": ["Neither supported printer profile matched the uploaded G-code metadata."],
            "detected": metadata,
            "validation_stages": stages,
            "printer_checks": printer_checks,
            "compatible_profiles": [],
            "compatible_printers": [],
            "next_step": "UPLOAD_GCODE",
        }

    if len(matches) > 1:
        stages.append(
            _stage(
                5,
                "SUPPORTED_PRINTER_MATCH",
                "FAIL",
                reason="More than one printer profile matched; profile definitions are ambiguous.",
            )
        )
        return {
            "status": "FAIL",
            "passed": False,
            "failed_stage": 5,
            "file": path.name,
            "format": "GCODE",
            "message": "Printer profile definitions are ambiguous; no printer was selected.",
            "errors": ["More than one supported printer profile matched."],
            "detected": metadata,
            "validation_stages": stages,
            "printer_checks": printer_checks,
            "compatible_profiles": matches,
            "compatible_printers": [SUPPORTED_PROFILES[x]["display_name"] for x in matches],
            "next_step": "UPLOAD_GCODE",
        }

    matched_profile = matches[0]
    matched_printer = SUPPORTED_PROFILES[matched_profile]["display_name"]
    stages.append(
        _stage(
            5,
            "SUPPORTED_PRINTER_MATCH",
            "PASS",
            compatible_profile=matched_profile,
            compatible_printer=matched_printer,
        )
    )

    return {
        "status": "PASS",
        "passed": True,
        "file": path.name,
        "format": "GCODE",
        "message": "G-code validation passed. Continue to compatible printer selection.",
        "detected": metadata,
        "validation_stages": stages,
        "printer_checks": printer_checks,
        "compatible_profiles": [matched_profile],
        "compatible_printers": [matched_printer],
        "compatible_profile": matched_profile,
        "compatible_printer": matched_printer,
        "next_step": "SELECT_PRINTER",
    }


# Backwards-friendly alias.
validate_gcode = validate_upload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Validate one G-code file, then compare it against both "
            "supported Prusa printer profiles."
        )
    )
    parser.add_argument("file", help="Path to the uploaded G-code file")
    args = parser.parse_args()
    print(json.dumps(validate_upload(args.file), indent=2))

