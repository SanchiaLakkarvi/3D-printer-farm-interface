from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass, field
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

# Binary G-code block types used by Prusa BGCode.
FILE_METADATA = 0
GCODE_BLOCK = 1
SLICER_METADATA = 2
PRINTER_METADATA = 3
PRINT_METADATA = 4
THUMBNAIL = 5

BLOCK_PARAM_SIZE = {
    FILE_METADATA: 2,
    GCODE_BLOCK: 2,
    SLICER_METADATA: 2,
    PRINTER_METADATA: 2,
    PRINT_METADATA: 2,
    THUMBNAIL: 6,
}

# The project currently supports these two configured printer profiles.
# NOTE: CORE One values below are confirmed by the uploaded sample.

SUPPORTED_PROFILES: dict[str, dict[str, Any]] = {
    "core_one_hf04": {
        "display_name": "Prusa CORE One HF0.4 nozzle",
        "printer_model": "COREONE",
        "printer_variant": "HF0.4",
        "printer_settings_keywords": ["CORE One", "HF0.4"],
        "nozzle_diameter": [0.4],
        "nozzle_high_flow": [1],
        "allow_abrasive": False,
        "required_features": {"input shaper"},
        "build_volume_mm": (250.0, 220.0, 270.0),
        "max_nozzle_temperature": 290.0,
        "max_bed_temperature": 120.0,
    },
    "xl_5t_is_04": {
        "display_name": "Original Prusa XL - 5T Input Shaper 0.4 nozzle",
        "printer_model": "XL5IS",
        "printer_variant": "0.4",
        "printer_settings_keywords": ["XL", "5T", "Input Shaper", "0.4"],
        "nozzle_diameter": [0.4, 0.4, 0.4, 0.4, 0.4],
        # The existing implementation intentionally does not require a
        # high-flow flag for this XL profile.
        "nozzle_high_flow": None,
        "allow_abrasive": False,
        "required_features": {"input shaper"},
        "build_volume_mm": (360.0, 360.0, 360.0),
        "max_nozzle_temperature": 290.0,
        "max_bed_temperature": 120.0,
    },
}

# A strict binary check needs decoded executable G-code, not metadata only.
# The official Prusa libbgcode command-line program can convert .bgcode to
# normal .gcode. If it is not installed, .bgcode is rejected
REQUIRE_FULL_BGCODE_EXECUTABLE_CHECK = True


class ValidationError(ValueError):
    """Raised for a validation-stage failure."""


class BinaryGCodeParseError(ValidationError):
    pass


class TextGCodeParseError(ValidationError):
    pass


@dataclass
class FormatResult:
    kind: str  # "BINARY" or "TEXT"
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

    # Text/executable checks. Binary files get these from an official
    # binary->ASCII conversion when available.
    metadata_history: dict[str, list[str]] = field(default_factory=dict)
    m862_1: list[dict[str, Any]] = field(default_factory=list)
    m862_3_models: list[str] = field(default_factory=list)
    m862_5_levels: list[int] = field(default_factory=list)
    m862_6_features: list[str] = field(default_factory=list)
    config_begin_count: int = 0
    config_end_count: int = 0
    config_complete: bool = False
    safe_end: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 1: file format validation
# ---------------------------------------------------------------------------

def validate_file_format(path: str | Path) -> FormatResult:
    """
    Validate the file container/extension before deep parsing.

    This stage deliberately does NOT require a G/M/T command inside the first
    256 KiB. Valid Prusa files can have large thumbnails/metadata before the
    first executable command. Full command validation happens in Stage 2.
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
                "The uploaded .bgcode file does not contain the expected binary G-code header."
            )
        return FormatResult(kind="BINARY", extension=ext)

    # ext == .gcode
    if is_binary_gcode:
        raise ValidationError(
            "The uploaded file extension is .gcode but the content is binary G-code."
        )

    if b"\x00" in sample:
        raise ValidationError(
            "The .gcode file contains binary/NUL data and is not valid text G-code."
        )

    return FormatResult(kind="TEXT", extension=ext)


# ---------------------------------------------------------------------------
# Stage 2A: binary G-code parser / CRC integrity
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
            f"Unsupported metadata encoding {metadata_encoding}; expected INI encoding 0."
        )

    if block.compression == 0:
        raw = block.payload
    elif block.compression == 1:
        try:
            raw = zlib.decompress(block.payload)
        except zlib.error as exc:
            raise BinaryGCodeParseError(
                f"Cannot decompress metadata block: {exc}"
            ) from exc
    else:
        # The validator can still parse the BGCode structure/CRC, but it cannot
        # decode compressed metadata types 2/3 without libbgcode/heatshrink.
        raise BinaryGCodeParseError(
            "This Python parser cannot decode metadata compression type "
            f"{block.compression}. Use the official libbgcode converter."
        )

    if len(raw) != block.uncompressed_size:
        raise BinaryGCodeParseError(
            "Metadata size mismatch: "
            f"expected {block.uncompressed_size}, got {len(raw)}."
        )

    return _parse_key_values(raw)


def parse_binary_gcode(path: str | Path) -> ParsedGCode:
    """Parse BGCode structure, verify block CRC32 values, and read metadata."""
    path = Path(path)
    data = path.read_bytes()

    if len(data) < 10:
        raise BinaryGCodeParseError("Binary G-code header is truncated.")

    magic, version, checksum_type = struct.unpack_from("<IIH", data, 0)
    if magic.to_bytes(4, "little") != BINARY_GCODE_MAGIC:
        raise BinaryGCodeParseError("Invalid binary G-code header.")
    if version != BINARY_GCODE_VERSION:
        raise BinaryGCodeParseError(
            f"Unsupported binary G-code version {version}; "
            f"supported version is {BINARY_GCODE_VERSION}."
        )
    if checksum_type not in (CHECKSUM_NONE, CHECKSUM_CRC32):
        raise BinaryGCodeParseError(
            f"Unsupported binary G-code checksum type {checksum_type}."
        )

    offset = 10
    blocks: list[BinaryGCodeBlock] = []

    while offset < len(data):
        block_start = offset
        if offset + 8 > len(data):
            raise BinaryGCodeParseError("Truncated binary G-code block header.")

        block_type, compression, uncompressed_size = struct.unpack_from(
            "<HHI", data, offset
        )
        offset += 8

        if block_type not in BLOCK_PARAM_SIZE:
            raise BinaryGCodeParseError(
                f"Unsupported/invalid binary G-code block type {block_type}."
            )
        if compression not in (0, 1, 2, 3):
            raise BinaryGCodeParseError(
                f"Unsupported/invalid compression type {compression}."
            )

        if compression == 0:
            compressed_size = uncompressed_size
        else:
            if offset + 4 > len(data):
                raise BinaryGCodeParseError("Truncated compressed block header.")
            compressed_size = struct.unpack_from("<I", data, offset)[0]
            offset += 4

        param_size = BLOCK_PARAM_SIZE[block_type]
        if offset + param_size + compressed_size > len(data):
            raise BinaryGCodeParseError("Truncated binary G-code block payload.")

        params = data[offset : offset + param_size]
        offset += param_size
        payload = data[offset : offset + compressed_size]
        offset += compressed_size

        crc_ok = True
        if checksum_type == CHECKSUM_CRC32:
            if offset + 4 > len(data):
                raise BinaryGCodeParseError("Binary G-code block is missing CRC32.")
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
        raise BinaryGCodeParseError("Binary G-code file contains no data blocks.")

    if not all(block.crc_ok for block in blocks):
        raise BinaryGCodeParseError(
            "CRC32 verification failed. The binary G-code is corrupted or modified."
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
        raise BinaryGCodeParseError(
            "Binary G-code file contains no executable G-code data blocks."
        )

    return ParsedGCode(
        kind="BINARY",
        file_metadata=file_meta,
        printer_metadata=printer_meta,
        print_metadata=print_meta,
        slicer_metadata=slicer_meta,
        gcode_blocks=gcode_blocks,
        integrity_ok=True,
    )


# ---------------------------------------------------------------------------
# Stage 2B: text G-code parser / structural integrity
# ---------------------------------------------------------------------------
_COMMENT_KV_RE = re.compile(r"^\s*;\s*([^=]+?)\s*=\s*(.*?)\s*$")
_COMMAND_RE = re.compile(
    r"^(?:N\d+\s+)?(?:G\d+(?:\.\d+)?|M\d+(?:\.\d+)?|T\d+)\b",
    re.IGNORECASE,
)


def _parameter_number(command: str, letter: str) -> float | None:
    match = re.search(
        rf"(?:^|\s){re.escape(letter)}\s*(-?\d+(?:\.\d+)?)\b",
        command,
        re.IGNORECASE,
    )
    return float(match.group(1)) if match else None


def _parameter_quoted_or_token(command: str, letter: str) -> str | None:
    quoted = re.search(
        rf'(?:^|\s){re.escape(letter)}\s*"([^"]+)"',
        command,
        re.IGNORECASE,
    )
    if quoted:
        return quoted.group(1).strip()

    token = re.search(
        rf"(?:^|\s){re.escape(letter)}\s*([^\s;]+)",
        command,
        re.IGNORECASE,
    )
    return token.group(1).strip() if token else None


def _parse_m862_command(command: str, parsed: ParsedGCode) -> None:
    upper = command.upper()

    if upper.startswith("M862.1"):
        nozzle = _parameter_number(command, "P")
        abrasive = _parameter_number(command, "A")
        high_flow = _parameter_number(command, "F")
        tool = _parameter_number(command, "T")
        parsed.m862_1.append(
            {
                "nozzle_diameter": nozzle,
                "abrasive": int(abrasive) if abrasive is not None else None,
                "high_flow": int(high_flow) if high_flow is not None else None,
                "tool": int(tool) if tool is not None else None,
                "raw": command,
            }
        )

    elif upper.startswith("M862.3"):
        model = _parameter_quoted_or_token(command, "P")
        if model:
            parsed.m862_3_models.append(model)

    elif upper.startswith("M862.5"):
        level = _parameter_number(command, "P")
        if level is not None:
            parsed.m862_5_levels.append(int(level))

    elif upper.startswith("M862.6"):
        feature = _parameter_quoted_or_token(command, "P")
        if feature:
            parsed.m862_6_features.append(feature)


def parse_text_gcode(path: str | Path) -> ParsedGCode:
    """Parse complete ASCII G-code and perform basic structural integrity checks."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise TextGCodeParseError("Cannot decode .gcode as UTF-8 text.") from exc

    parsed = ParsedGCode(
        kind="TEXT",
        file_metadata={},
        printer_metadata={},
        print_metadata={},
        slicer_metadata={},
        gcode_blocks=0,
        integrity_ok=False,
        safe_end={
            "nozzle_heater_off": False,
            "bed_heater_off": False,
            "fan_off": False,
            "motors_off": False,
        },
    )

    metadata: dict[str, str] = {}
    metadata_history: dict[str, list[str]] = {}
    command_count = 0
    executable_commands: list[str] = []

    config_open = False
    config_seen_complete = False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lower = stripped.lower()

        if stripped.startswith(";"):
            if lower == "; prusaslicer_config = begin":
                parsed.config_begin_count += 1
                if config_open:
                    raise TextGCodeParseError(
                        "Nested/duplicate PrusaSlicer config begin marker found."
                    )
                config_open = True

            elif lower == "; prusaslicer_config = end":
                parsed.config_end_count += 1
                if not config_open:
                    raise TextGCodeParseError(
                        "PrusaSlicer config end marker found without a begin marker."
                    )
                config_open = False
                config_seen_complete = True

            match = _COMMENT_KV_RE.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip().strip('"')
                metadata[key] = value
                metadata_history.setdefault(key, []).append(value)
            continue

        command_part = stripped.split(";", 1)[0].strip()
        if not _COMMAND_RE.match(command_part):
            continue

        command_count += 1
        executable_commands.append(command_part)

        if command_part.upper().startswith("M862."):
            _parse_m862_command(command_part, parsed)

    if command_count == 0:
        raise TextGCodeParseError("No executable G/M/T G-code commands were found.")

    # For this controlled, PrusaSlicer config completeness is an
    # integrity requirement for text G-code because compatibility settings are
    # taken from that profile block.
    if parsed.config_begin_count != 1 or parsed.config_end_count != 1:
        raise TextGCodeParseError(
            "PrusaSlicer config block is incomplete or duplicated: expected exactly "
            "one 'prusaslicer_config = begin' and one 'prusaslicer_config = end'."
        )
    if config_open or not config_seen_complete:
        raise TextGCodeParseError("PrusaSlicer config block is truncated/incomplete.")

    # Check the final portion of the executable stream. Exact endings vary, so
    # nozzle+bed heater shutdown are required; fan/motor shutdown are reported
    # and used as extra integrity signals.
    tail = executable_commands[-250:]
    for command in tail:
        upper = command.upper()
        if re.match(r"^M104\b.*(?:^|\s)S0(?:\.0+)?\b", upper):
            parsed.safe_end["nozzle_heater_off"] = True
        if re.match(r"^M140\b.*(?:^|\s)S0(?:\.0+)?\b", upper):
            parsed.safe_end["bed_heater_off"] = True
        if re.match(r"^M107\b", upper):
            parsed.safe_end["fan_off"] = True
        if re.match(r"^(?:M84|M18)\b", upper):
            parsed.safe_end["motors_off"] = True

    if not parsed.safe_end["nozzle_heater_off"]:
        raise TextGCodeParseError(
            "End-of-file safety check failed: no final nozzle-heater-off command (M104 S0) found."
        )
    if not parsed.safe_end["bed_heater_off"]:
        raise TextGCodeParseError(
            "End-of-file safety check failed: no final bed-heater-off command (M140 S0) found."
        )

    if not parsed.safe_end["fan_off"]:
        parsed.warnings.append("No M107 fan-off command was found near the end of the file.")
    if not parsed.safe_end["motors_off"]:
        parsed.warnings.append("No M84/M18 motor-off command was found near the end of the file.")

    parsed.file_metadata = metadata
    parsed.printer_metadata = metadata
    parsed.print_metadata = metadata
    parsed.slicer_metadata = metadata
    parsed.metadata_history = metadata_history
    parsed.gcode_blocks = command_count
    parsed.config_complete = True
    parsed.integrity_ok = True
    return parsed


def _convert_bgcode_to_text(path: Path) -> Path:
    """
    Convert BGCode to ASCII using Prusa's official libbgcode 'bgcode' CLI.

    The command documented by Prusa is simply:
        bgcode file.bgcode
    which produces file.gcode.
    """
    executable = shutil.which("bgcode") or shutil.which("bgcode.exe")
    if not executable:
        raise ValidationError(
            "Full .bgcode validation requires the official Prusa libbgcode 'bgcode' "
            "converter on PATH so executable M862/end-of-file checks can be performed. "
            "Install/bundle libbgcode, or upload the converted .gcode file instead."
        )

    temp_dir = Path(tempfile.mkdtemp(prefix="uwa_bgcode_"))
    temp_input = temp_dir / path.name
    shutil.copy2(path, temp_input)

    try:
        completed = subprocess.run(
            [executable, str(temp_input)],
            cwd=temp_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValidationError(f"Could not run bgcode converter: {exc}") from exc

    output = temp_input.with_suffix(".gcode")
    if completed.returncode != 0 or not output.is_file():
        error = (completed.stderr or completed.stdout or "conversion failed").strip()
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ValidationError(f"BGCode to ASCII conversion failed: {error}")

    return output


def parse_gcode(path: str | Path, fmt: FormatResult) -> tuple[ParsedGCode, ParsedGCode | None, Path | None]:
    """
    Return:
      native_parsed, executable_text_parsed, temp_directory

    For text G-code, both parsed objects are the same and temp_directory is None.
    For BGCode, native_parsed validates binary structure/CRC, then an official
    conversion supplies the executable text checks.
    """
    path = Path(path)

    if fmt.kind == "TEXT":
        parsed = parse_text_gcode(path)
        return parsed, parsed, None

    if fmt.kind == "BINARY":
        native = parse_binary_gcode(path)

        if not REQUIRE_FULL_BGCODE_EXECUTABLE_CHECK:
            return native, None, None

        converted = _convert_bgcode_to_text(path)
        temp_dir = converted.parent
        text_parsed = parse_text_gcode(converted)
        return native, text_parsed, temp_dir

    raise ValidationError(f"Unsupported detected format {fmt.kind!r}.")


# ---------------------------------------------------------------------------
# Stage 3: normalize metadata
# ---------------------------------------------------------------------------

def _first_value(parsed: ParsedGCode, *keys: str) -> str | None:
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


def _check_metadata_consistency(parsed: ParsedGCode) -> None:
    """Reject conflicting duplicate critical metadata in text G-code."""
    if parsed.kind != "TEXT":
        return

    critical = {
        "printer_model",
        "printer_variant",
        "printer_settings_id",
        "nozzle_diameter",
        "nozzle_high_flow",
        "filament_type",
        "filament_abrasive",
        "bed_shape",
        "max_print_height",
        "max_layer_z",
    }

    numeric_csv_keys = {
        "nozzle_diameter",
        "nozzle_high_flow",
        "filament_abrasive",
        "max_print_height",
        "max_layer_z",
    }

    conflicts: list[str] = []
    for key in critical:
        values = [value.strip() for value in parsed.metadata_history.get(key, []) if value.strip()]
        if not values:
            continue

        if key in numeric_csv_keys:
            normalized_numeric: set[tuple[float, ...]] = set()
            parse_failed = False
            for value in values:
                parsed_values = _csv_floats(value)
                if not parsed_values:
                    parse_failed = True
                    break
                normalized_numeric.add(tuple(round(x, 8) for x in parsed_values))
            if parse_failed:
                normalized = set(values)
                if len(normalized) > 1:
                    conflicts.append(f"{key}={sorted(normalized)!r}")
            elif len(normalized_numeric) > 1:
                conflicts.append(f"{key}={values!r}")
        else:
            normalized = set(values)
            if len(normalized) > 1:
                conflicts.append(f"{key}={sorted(normalized)!r}")

    if conflicts:
        raise ValidationError(
            "Conflicting critical metadata was found in the G-code: "
            + "; ".join(conflicts)
        )


def extract_metadata(parsed: ParsedGCode) -> dict[str, str | None]:
    _check_metadata_consistency(parsed)

    detected = {
        "producer": _first_value(parsed, "Producer", "producer"),
        "printer_model": _first_value(parsed, "printer_model"),
        "printer_variant": _first_value(parsed, "printer_variant"),
        "printer_settings_id": _first_value(parsed, "printer_settings_id"),
        "printer_technology": _first_value(parsed, "printer_technology"),
        "print_settings_id": _first_value(parsed, "print_settings_id"),
        "nozzle_diameter": _first_value(parsed, "nozzle_diameter"),
        "nozzle_high_flow": _first_value(parsed, "nozzle_high_flow"),
        "filament_type": _first_value(parsed, "filament_type"),
        "filament_abrasive": _first_value(parsed, "filament_abrasive"),
        "filament_colour": _first_value(parsed, "filament_colour"),
        "filament_settings_id": _first_value(parsed, "filament_settings_id"),
        "bed_shape": _first_value(parsed, "bed_shape"),
        "max_print_height": _first_value(parsed, "max_print_height"),
        "max_layer_z": _first_value(parsed, "max_layer_z"),
        "objects_info": _first_value(parsed, "objects_info"),
        "temperature": _first_value(parsed, "temperature"),
        "bed_temperature": _first_value(parsed, "bed_temperature"),
        "first_layer_temperature": _first_value(parsed, "first_layer_temperature"),
        "first_layer_bed_temperature": _first_value(
            parsed, "first_layer_bed_temperature"
        ),
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
        "filament_used_mm": _first_value(parsed, "filament used [mm]"),
        "filament_used_cm3": _first_value(parsed, "filament used [cm3]"),
        "filament_cost": _first_value(parsed, "filament cost"),
    }

    # Minimum information needed for the controlled compatibility checks.
    required = (
        "printer_model",
        "printer_variant",
        "printer_settings_id",
        "nozzle_diameter",
        "filament_type",
        "filament_abrasive",
        "bed_shape",
        "max_print_height",
        "max_layer_z",
    )
    missing = [key for key in required if not detected.get(key)]
    if missing:
        raise ValidationError(
            "Required printer/material/build metadata is missing: "
            + ", ".join(missing)
            + "."
        )

    return detected


# ---------------------------------------------------------------------------
# Helpers for profile/safety checks
# ---------------------------------------------------------------------------

def _csv_floats(value: str | None) -> list[float]:
    if not value:
        return []
    parts = re.split(r"[,;]", value)
    try:
        return [float(part.strip()) for part in parts if part.strip()]
    except ValueError:
        return []


def _csv_ints(value: str | None) -> list[int]:
    if not value:
        return []
    parts = re.split(r"[,;]", value)
    try:
        return [int(float(part.strip())) for part in parts if part.strip()]
    except ValueError:
        return []


def _same_floats(actual: list[float], expected: list[float]) -> bool:
    return len(actual) == len(expected) and all(
        abs(a - b) <= 1e-6 for a, b in zip(actual, expected)
    )


def _single_float(value: str | None, field_name: str) -> float:
    values = _csv_floats(value)
    if len(values) != 1:
        raise ValidationError(
            f"{field_name} must contain exactly one numeric value; got {value!r}."
        )
    return values[0]


def _parse_bed_shape(value: str | None) -> tuple[float, float, float, float]:
    if not value:
        raise ValidationError("bed_shape metadata is missing.")

    points = re.findall(r"(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)", value)
    if len(points) < 3:
        raise ValidationError(f"Cannot parse bed_shape={value!r}.")

    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def _object_xy_bounds(objects_info: str | None) -> tuple[float, float, float, float] | None:
    if not objects_info:
        return None

    try:
        data = json.loads(objects_info)
    except json.JSONDecodeError:
        return None

    points: list[tuple[float, float]] = []

    def add_pairs(value: Any) -> None:
        if isinstance(value, list):
            if (
                len(value) >= 2
                and isinstance(value[0], (int, float))
                and isinstance(value[1], (int, float))
            ):
                points.append((float(value[0]), float(value[1])))
                return
            for item in value:
                add_pairs(item)
        elif isinstance(value, dict):
            for subvalue in value.values():
                add_pairs(subvalue)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, subvalue in value.items():
                key_lower = key.lower()
                if any(
                    token in key_lower
                    for token in (
                        "polygon",
                        "bounding_box",
                        "convex_hull",
                        "object_center",
                    )
                ):
                    add_pairs(subvalue)
                elif key_lower == "objects":
                    visit(subvalue)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _validate_temperature_list(
    value: str | None,
    field_name: str,
    maximum: float,
    allow_zero: bool = False,
) -> list[float]:
    if value in (None, ""):
        return []

    values = _csv_floats(value)
    if not values:
        raise ValidationError(f"Cannot parse {field_name}={value!r}.")

    for temp in values:
        if temp < 0 or (temp == 0 and not allow_zero):
            raise ValidationError(f"{field_name} contains invalid temperature {temp}°C.")
        if temp > maximum:
            raise ValidationError(
                f"{field_name}={temp}°C exceeds configured printer maximum {maximum}°C."
            )
    return values


# ---------------------------------------------------------------------------
# Stage 4: executable M862 cross-check
# ---------------------------------------------------------------------------

def validate_m862_cross_check(
    metadata: dict[str, str | None],
    executable: ParsedGCode,
    profile: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if not executable.m862_1:
        errors.append("Missing M862.1 nozzle compatibility command.")
    if not executable.m862_3_models:
        errors.append("Missing M862.3 printer-model compatibility command.")
    if not executable.m862_5_levels:
        errors.append("Missing M862.5 G-code-level compatibility command.")
    if not executable.m862_6_features:
        errors.append("Missing M862.6 firmware-feature compatibility command.")

    metadata_model = metadata.get("printer_model")
    if executable.m862_3_models and metadata_model not in executable.m862_3_models:
        errors.append(
            f"M862.3 model {executable.m862_3_models!r} does not match "
            f"metadata printer_model={metadata_model!r}."
        )

    metadata_nozzles = _csv_floats(metadata.get("nozzle_diameter"))
    m862_nozzles = [
        entry["nozzle_diameter"]
        for entry in executable.m862_1
        if entry.get("nozzle_diameter") is not None
    ]
    if metadata_nozzles and m862_nozzles:
        expected_set = {round(x, 6) for x in metadata_nozzles}
        command_set = {round(float(x), 6) for x in m862_nozzles}
        if not command_set.issubset(expected_set):
            errors.append(
                f"M862.1 nozzle values {sorted(command_set)!r} do not agree with "
                f"metadata nozzle_diameter={metadata_nozzles!r}."
            )

    abrasive_meta = _csv_ints(metadata.get("filament_abrasive"))
    high_flow_meta = _csv_ints(metadata.get("nozzle_high_flow"))

    for entry in executable.m862_1:
        if entry.get("abrasive") is not None and abrasive_meta:
            if entry["abrasive"] not in abrasive_meta:
                errors.append(
                    f"M862.1 abrasive flag A{entry['abrasive']} disagrees with "
                    f"filament_abrasive={abrasive_meta!r}."
                )
        if entry.get("high_flow") is not None and high_flow_meta:
            if entry["high_flow"] not in high_flow_meta:
                errors.append(
                    f"M862.1 high-flow flag F{entry['high_flow']} disagrees with "
                    f"nozzle_high_flow={high_flow_meta!r}."
                )

    required_features = {
        feature.lower() for feature in profile.get("required_features", set())
    }
    actual_features = {feature.lower() for feature in executable.m862_6_features}
    missing_features = sorted(required_features - actual_features)
    if missing_features:
        errors.append(
            "Missing required M862.6 feature check(s): " + ", ".join(missing_features)
        )

    if errors:
        raise ValidationError(" ".join(errors))

    return {
        "m862_1": executable.m862_1,
        "m862_3_models": executable.m862_3_models,
        "m862_5_levels": executable.m862_5_levels,
        "m862_6_features": executable.m862_6_features,
    }


# ---------------------------------------------------------------------------
# Stage 5: printer profile + build volume + temperature checks
# ---------------------------------------------------------------------------

def _match_profile(
    metadata: dict[str, str | None], profile_id: str
) -> tuple[bool, list[str], dict[str, Any]]:
    expected = SUPPORTED_PROFILES[profile_id]
    reasons: list[str] = []
    details: dict[str, Any] = {}

    model = metadata.get("printer_model")
    variant = metadata.get("printer_variant")
    settings_id = metadata.get("printer_settings_id") or ""
    nozzles = _csv_floats(metadata.get("nozzle_diameter"))
    high_flow = _csv_ints(metadata.get("nozzle_high_flow"))
    abrasive = _csv_ints(metadata.get("filament_abrasive"))

    if model != expected["printer_model"]:
        reasons.append(
            f"printer_model={model!r}; expected {expected['printer_model']!r}"
        )

    if variant != expected["printer_variant"]:
        reasons.append(
            f"printer_variant={variant!r}; expected {expected['printer_variant']!r}"
        )

    if not _same_floats(nozzles, expected["nozzle_diameter"]):
        reasons.append(
            f"nozzle_diameter={nozzles}; expected {expected['nozzle_diameter']}"
        )

    expected_hf = expected["nozzle_high_flow"]
    if expected_hf is not None and high_flow != expected_hf:
        reasons.append(f"nozzle_high_flow={high_flow}; expected {expected_hf}")

    for keyword in expected.get("printer_settings_keywords", []):
        if keyword.lower() not in settings_id.lower():
            reasons.append(
                f"printer_settings_id={settings_id!r} is missing keyword {keyword!r}"
            )

    if not expected.get("allow_abrasive", True) and any(value != 0 for value in abrasive):
        reasons.append(
            "filament_abrasive indicates an abrasive material, but this configured "
            "standard nozzle profile does not allow abrasive filament."
        )

    # Build-volume checks.
    try:
        bed_min_x, bed_min_y, bed_max_x, bed_max_y = _parse_bed_shape(
            metadata.get("bed_shape")
        )
        bed_width = bed_max_x - bed_min_x
        bed_depth = bed_max_y - bed_min_y
        profile_x, profile_y, profile_z = expected["build_volume_mm"]

        details["bed_shape_mm"] = [bed_width, bed_depth]
        details["printer_build_volume_mm"] = list(expected["build_volume_mm"])

        if bed_width > profile_x + 1e-6 or bed_depth > profile_y + 1e-6:
            reasons.append(
                f"bed_shape {bed_width}x{bed_depth} mm exceeds printer build area "
                f"{profile_x}x{profile_y} mm."
            )

        max_print_height = _single_float(
            metadata.get("max_print_height"), "max_print_height"
        )
        max_layer_z = _single_float(metadata.get("max_layer_z"), "max_layer_z")
        details["max_print_height_mm"] = max_print_height
        details["job_max_layer_z_mm"] = max_layer_z

        if max_print_height > profile_z + 1e-6:
            reasons.append(
                f"max_print_height={max_print_height} mm exceeds printer Z={profile_z} mm."
            )
        if max_layer_z > profile_z + 1e-6:
            reasons.append(
                f"max_layer_z={max_layer_z} mm exceeds printer Z={profile_z} mm."
            )

        object_bounds = _object_xy_bounds(metadata.get("objects_info"))
        if object_bounds is not None:
            min_x, min_y, max_x, max_y = object_bounds
            details["object_xy_bounds_mm"] = [min_x, min_y, max_x, max_y]
            if (
                min_x < bed_min_x - 1e-6
                or min_y < bed_min_y - 1e-6
                or max_x > bed_max_x + 1e-6
                or max_y > bed_max_y + 1e-6
            ):
                reasons.append(
                    "Object XY bounds fall outside the G-code bed_shape."
                )
    except ValidationError as exc:
        reasons.append(str(exc))

    # Hardware temperature caps. This does not replace UWA material-policy
    # ranges; it prevents values above the configured machine limits.
    try:
        details["temperature_c"] = _validate_temperature_list(
            metadata.get("temperature"),
            "temperature",
            expected["max_nozzle_temperature"],
        )
        details["first_layer_temperature_c"] = _validate_temperature_list(
            metadata.get("first_layer_temperature"),
            "first_layer_temperature",
            expected["max_nozzle_temperature"],
        )
        details["bed_temperature_c"] = _validate_temperature_list(
            metadata.get("bed_temperature"),
            "bed_temperature",
            expected["max_bed_temperature"],
            allow_zero=True,
        )
        details["first_layer_bed_temperature_c"] = _validate_temperature_list(
            metadata.get("first_layer_bed_temperature"),
            "first_layer_bed_temperature",
            expected["max_bed_temperature"],
            allow_zero=True,
        )
    except ValidationError as exc:
        reasons.append(str(exc))

    return not reasons, reasons, details


def check_both_printers(
    metadata: dict[str, str | None],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    checks: dict[str, dict[str, Any]] = {}
    matches: list[str] = []

    for profile_id, profile in SUPPORTED_PROFILES.items():
        matched, reasons, details = _match_profile(metadata, profile_id)
        checks[profile_id] = {
            "printer": profile["display_name"],
            "matched": matched,
            "result": "MATCH" if matched else "NO_MATCH",
            "reasons": reasons,
            "details": details,
        }
        if matched:
            matches.append(profile_id)

    return checks, matches



# ---------------------------------------------------------------------------
# Result helpers
# ---------------------------------------------------------------------------

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


def _failure(
    *,
    path: Path,
    stage_number: int,
    stages: list[dict[str, Any]],
    message: str,
    error: str,
    printer_checks: dict[str, dict[str, Any]] | None = None,
    detected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "FAIL",
        "passed": False,
        "failed_stage": stage_number,
        "file": path.name,
        "message": message,
        "errors": [error],
        "validation_stages": stages,
        "printer_checks": printer_checks
        if printer_checks is not None
        else _not_checked_printers("Not checked because an earlier validation stage failed."),
        "compatible_profiles": [],
        "compatible_printers": [],
        "next_step": "UPLOAD_GCODE",
    }
    if detected is not None:
        result["detected"] = detected
    return result


# ---------------------------------------------------------------------------
# Full validation flow
# ---------------------------------------------------------------------------

def validate_upload(path: str | Path) -> dict[str, Any]:
    """
    Validation flow:

      1. FILE FORMAT
      2. PARSE + INTEGRITY
      3. READ METADATA
      4. M862 EXECUTABLE CROSS-CHECK
      5. CHECK BOTH PRINTER PROFILES + BUILD/TEMPERATURE
      6. EXACTLY ONE SUPPORTED PROFILE

    PASS moves to SELECT_PRINTER only. It does not queue or start a print.
    """
    path = Path(path)
    stages: list[dict[str, Any]] = []
    temp_dir: Path | None = None

    try:
        # Stage 1 -----------------------------------------------------------
        try:
            fmt = validate_file_format(path)
        except (OSError, ValidationError) as exc:
            stages.append(_stage(1, "FILE_FORMAT_VALIDATION", "FAIL", reason=str(exc)))
            return _failure(
                path=path,
                stage_number=1,
                stages=stages,
                message="Invalid G-code file format.",
                error=str(exc),
            )

        stages.append(
            _stage(
                1,
                "FILE_FORMAT_VALIDATION",
                "PASS",
                detected_format="BGCODE" if fmt.kind == "BINARY" else "GCODE",
                extension=fmt.extension,
            )
        )

        # Stage 2 -----------------------------------------------------------
        try:
            parsed, executable, temp_dir = parse_gcode(path, fmt)
        except (OSError, UnicodeDecodeError, ValidationError) as exc:
            stages.append(_stage(2, "PARSE_AND_INTEGRITY", "FAIL", reason=str(exc)))
            return _failure(
                path=path,
                stage_number=2,
                stages=stages,
                message="G-code could not be parsed or failed integrity validation.",
                error=str(exc),
            )

        if executable is None:
            stages.append(
                _stage(
                    2,
                    "PARSE_AND_INTEGRITY",
                    "PASS",
                    parsed_format=parsed.kind,
                    gcode_blocks_or_commands=parsed.gcode_blocks,
                    integrity_ok=parsed.integrity_ok,
                )
            )
        else:
            stages.append(
                _stage(
                    2,
                    "PARSE_AND_INTEGRITY",
                    "PASS",
                    parsed_format=parsed.kind,
                    gcode_blocks_or_commands=parsed.gcode_blocks,
                    integrity_ok=parsed.integrity_ok,
                    config_complete=executable.config_complete,
                    safe_end=executable.safe_end,
                    warnings=executable.warnings,
                )
            )

        # Stage 3 -----------------------------------------------------------
        # For BGCode, native metadata is preferred. For text, parsed==executable.
        try:
            metadata = extract_metadata(parsed)
        except ValidationError as exc:
            stages.append(_stage(3, "READ_METADATA", "FAIL", reason=str(exc)))
            return _failure(
                path=path,
                stage_number=3,
                stages=stages,
                message="Required printer/material/build metadata could not be read.",
                error=str(exc),
            )

        stages.append(
            _stage(
                3,
                "READ_METADATA",
                "PASS",
                printer_model=metadata.get("printer_model"),
                printer_variant=metadata.get("printer_variant"),
                printer_settings_id=metadata.get("printer_settings_id"),
                nozzle_diameter=metadata.get("nozzle_diameter"),
                nozzle_high_flow=metadata.get("nozzle_high_flow"),
                filament_type=metadata.get("filament_type"),
                filament_abrasive=metadata.get("filament_abrasive"),
                max_layer_z=metadata.get("max_layer_z"),
            )
        )

        # Stage 4: determine candidate profile from metadata first so M862.6
        # required features can be checked against the intended profile.
        printer_checks, candidate_matches = check_both_printers(metadata)

        if len(candidate_matches) == 0:
            stages.append(
                _stage(
                    4,
                    "M862_EXECUTABLE_CROSS_CHECK",
                    "NOT_CHECKED",
                    reason="No printer profile matched the metadata.",
                )
            )
            stages.append(
                _stage(
                    5,
                    "CHECK_BOTH_PRINTERS",
                    "PASS",
                    printers_checked=list(SUPPORTED_PROFILES.keys()),
                    matching_profiles=[],
                )
            )
            stages.append(
                _stage(
                    6,
                    "SUPPORTED_PRINTER_MATCH",
                    "FAIL",
                    reason="Neither supported printer profile matched.",
                )
            )
            return _failure(
                path=path,
                stage_number=6,
                stages=stages,
                message=(
                    "G-code is structurally valid, but it is not compatible with either "
                    "supported printer profile. Re-slice for CORE One HF0.4 or "
                    "XL 5T Input Shaper 0.4."
                ),
                error="Neither supported printer profile matched the uploaded G-code.",
                printer_checks=printer_checks,
                detected=metadata,
            )

        if len(candidate_matches) > 1:
            stages.append(
                _stage(
                    4,
                    "M862_EXECUTABLE_CROSS_CHECK",
                    "NOT_CHECKED",
                    reason="Metadata matches more than one profile.",
                )
            )
            stages.append(
                _stage(
                    5,
                    "CHECK_BOTH_PRINTERS",
                    "PASS",
                    printers_checked=list(SUPPORTED_PROFILES.keys()),
                    matching_profiles=candidate_matches,
                )
            )
            stages.append(
                _stage(
                    6,
                    "SUPPORTED_PRINTER_MATCH",
                    "FAIL",
                    reason="More than one printer profile matched; definitions are ambiguous.",
                )
            )
            return _failure(
                path=path,
                stage_number=6,
                stages=stages,
                message="Printer profile definitions are ambiguous.",
                error="More than one supported printer profile matched.",
                printer_checks=printer_checks,
                detected=metadata,
            )

        candidate_profile = candidate_matches[0]

        if executable is None:
            exc = ValidationError(
                "Executable-command validation is unavailable for this BGCode file."
            )
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "FAIL", reason=str(exc)))
            return _failure(
                path=path,
                stage_number=4,
                stages=stages,
                message="Could not verify executable printer compatibility commands.",
                error=str(exc),
                printer_checks=printer_checks,
                detected=metadata,
            )

        try:
            m862_details = validate_m862_cross_check(
                metadata,
                executable,
                SUPPORTED_PROFILES[candidate_profile],
            )
        except ValidationError as exc:
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "FAIL", reason=str(exc)))
            return _failure(
                path=path,
                stage_number=4,
                stages=stages,
                message="G-code metadata does not agree with executable compatibility checks.",
                error=str(exc),
                printer_checks=printer_checks,
                detected=metadata,
            )

        stages.append(
            _stage(4, "M862_EXECUTABLE_CROSS_CHECK", "PASS", **m862_details)
        )

        # Stage 5 -----------------------------------------------------------
        stages.append(
            _stage(
                5,
                "CHECK_BOTH_PRINTERS",
                "PASS",
                printers_checked=list(SUPPORTED_PROFILES.keys()),
                matching_profiles=candidate_matches,
            )
        )

        # Stage 6 -----------------------------------------------------------
        matched_profile = candidate_profile
        matched_printer = SUPPORTED_PROFILES[matched_profile]["display_name"]
        stages.append(
            _stage(
                6,
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
            "format": "BGCODE" if fmt.kind == "BINARY" else "GCODE",
            "message": "G-code validation passed. Continue to compatible printer selection.",
            "detected": metadata,
            "validation_stages": stages,
            "printer_checks": printer_checks,
            "compatible_profiles": [matched_profile],
            "compatible_printers": [matched_printer],
            "compatible_profile": matched_profile,
            "compatible_printer": matched_printer,
            "required_material": metadata.get("filament_type"),
            "slicer_filament_colour": metadata.get("filament_colour"),
            "estimated_print_time": metadata.get("estimated_print_time"),
            "filament_used_g": metadata.get("filament_used_g"),
            "next_step": "SELECT_PRINTER",
        }

    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


validate_gcode = validate_upload


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Validate one Prusa .gcode/.bgcode file against the two supported "
            "UWA printer profiles."
        )
    )
    parser.add_argument("file", help="Path to the uploaded G-code file")
    args = parser.parse_args()

    print(json.dumps(validate_upload(args.file), indent=2))

