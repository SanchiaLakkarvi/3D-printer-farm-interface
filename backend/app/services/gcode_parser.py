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

from app.schemas.gcode import BinaryGCodeBlock, FormatResult, ParsedGCode

ALLOWED_EXTENSIONS = {".gcode", ".bgcode"}
BINARY_GCODE_MAGIC = b"GCDE"
BINARY_GCODE_VERSION = 1
CHECKSUM_NONE = 0
CHECKSUM_CRC32 = 1

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


class ValidationError(ValueError):
    """Raised for a validation-stage failure."""


class BinaryGCodeParseError(ValidationError):
    pass


class TextGCodeParseError(ValidationError):
    pass


_COMMENT_KV_RE = re.compile(r"^\s*;\s*([^=]+?)\s*=\s*(.*?)\s*$")
_COMMAND_RE = re.compile(
    r"^(?:N\d+\s+)?(?:G\d+(?:\.\d+)?|M\d+(?:\.\d+)?|T\d+)\b",
    re.IGNORECASE,
)


def validate_file_format(path: str | Path) -> FormatResult:
    path = Path(path)

    if not path.is_file():
        raise ValidationError("Uploaded file does not exist or is not a regular file.")
    if path.stat().st_size == 0:
        raise ValidationError("Uploaded file is empty.")

    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file extension {ext or '<none>'!r}. Only .gcode and .bgcode are accepted."
        )

    with path.open("rb") as handle:
        sample = handle.read(256 * 1024)

    is_binary_gcode = sample.startswith(BINARY_GCODE_MAGIC)

    if ext == ".bgcode":
        if not is_binary_gcode:
            raise ValidationError(
                "The uploaded .bgcode file does not contain the expected binary G-code header."
            )
        return FormatResult(kind="BINARY", extension=ext)

    if is_binary_gcode:
        raise ValidationError("The uploaded file extension is .gcode but the content is binary G-code.")

    if b"\x00" in sample:
        raise ValidationError("The .gcode file contains binary/NUL data and is not valid text G-code.")

    return FormatResult(kind="TEXT", extension=ext)


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
            raise BinaryGCodeParseError(f"Cannot decompress metadata block: {exc}") from exc
    else:
        raise BinaryGCodeParseError(
            f"This Python parser cannot decode metadata compression type {block.compression}. "
            "Use the official libbgcode converter."
        )

    if len(raw) != block.uncompressed_size:
        raise BinaryGCodeParseError(
            f"Metadata size mismatch: expected {block.uncompressed_size}, got {len(raw)}."
        )

    return _parse_key_values(raw)


def parse_binary_gcode(path: str | Path) -> ParsedGCode:
    path = Path(path)
    data = path.read_bytes()

    if len(data) < 10:
        raise BinaryGCodeParseError("Binary G-code header is truncated.")

    magic, version, checksum_type = struct.unpack_from("<IIH", data, 0)
    if magic.to_bytes(4, "little") != BINARY_GCODE_MAGIC:
        raise BinaryGCodeParseError("Invalid binary G-code header.")
    if version != BINARY_GCODE_VERSION:
        raise BinaryGCodeParseError(
            f"Unsupported binary G-code version {version}; supported version is {BINARY_GCODE_VERSION}."
        )
    if checksum_type not in (CHECKSUM_NONE, CHECKSUM_CRC32):
        raise BinaryGCodeParseError(f"Unsupported binary G-code checksum type {checksum_type}.")

    offset = 10
    blocks: list[BinaryGCodeBlock] = []

    while offset < len(data):
        block_start = offset
        if offset + 8 > len(data):
            raise BinaryGCodeParseError("Truncated binary G-code block header.")

        block_type, compression, uncompressed_size = struct.unpack_from("<HHI", data, offset)
        offset += 8

        if block_type not in BLOCK_PARAM_SIZE:
            raise BinaryGCodeParseError(f"Unsupported/invalid binary G-code block type {block_type}.")
        if compression not in (0, 1, 2, 3):
            raise BinaryGCodeParseError(f"Unsupported/invalid compression type {compression}.")

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

        params = data[offset: offset + param_size]
        offset += param_size
        payload = data[offset: offset + compressed_size]
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
        raise BinaryGCodeParseError("CRC32 verification failed. The binary G-code is corrupted or modified.")

    file_metadata: dict[str, str] = {}
    printer_metadata: dict[str, str] = {}
    print_metadata: dict[str, str] = {}
    slicer_metadata: dict[str, str] = {}
    gcode_blocks = 0

    for block in blocks:
        if block.block_type == FILE_METADATA:
            file_metadata.update(_decode_metadata_block(block))
        elif block.block_type == PRINTER_METADATA:
            printer_metadata.update(_decode_metadata_block(block))
        elif block.block_type == PRINT_METADATA:
            print_metadata.update(_decode_metadata_block(block))
        elif block.block_type == SLICER_METADATA:
            slicer_metadata.update(_decode_metadata_block(block))
        elif block.block_type == GCODE_BLOCK:
            gcode_blocks += 1

    if gcode_blocks == 0:
        raise BinaryGCodeParseError("Binary G-code file contains no executable G-code data blocks.")

    return ParsedGCode(
        kind="BINARY",
        file_metadata=file_metadata,
        printer_metadata=printer_metadata,
        print_metadata=print_metadata,
        slicer_metadata=slicer_metadata,
        gcode_blocks=gcode_blocks,
        integrity_ok=True,
    )


def _parameter_number(command: str, letter: str) -> float | None:
    match = re.search(rf"(?:^|\s){re.escape(letter)}\s*(-?\d+(?:\.\d+)?)\b", command, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _parameter_quoted_or_token(command: str, letter: str) -> str | None:
    quoted = re.search(rf'(?:^|\s){re.escape(letter)}\s*"([^"]+)"', command, re.IGNORECASE)
    if quoted:
        return quoted.group(1).strip()

    token = re.search(rf"(?:^|\s){re.escape(letter)}\s*([^\s;]+)", command, re.IGNORECASE)
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

        if stripped.startswith(";"):
            if stripped.lower() == "; prusaslicer_config = begin":
                parsed.config_begin_count += 1
                if config_open:
                    raise TextGCodeParseError("Nested/duplicate PrusaSlicer config begin marker found.")
                config_open = True
            elif stripped.lower() == "; prusaslicer_config = end":
                parsed.config_end_count += 1
                if not config_open:
                    raise TextGCodeParseError("PrusaSlicer config end marker found without a begin marker.")
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

    if parsed.config_begin_count != 1 or parsed.config_end_count != 1:
        raise TextGCodeParseError(
            "PrusaSlicer config block is incomplete or duplicated: expected exactly one 'prusaslicer_config = begin' and one 'prusaslicer_config = end'."
        )
    if config_open or not config_seen_complete:
        raise TextGCodeParseError("PrusaSlicer config block is truncated/incomplete.")

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
    executable = shutil.which("bgcode") or shutil.which("bgcode.exe")
    if not executable:
        raise ValidationError(
            "Full .bgcode validation requires the official Prusa libbgcode 'bgcode' converter on PATH so executable M862/end-of-file checks can be performed. Install/bundle libbgcode, or upload the converted .gcode file instead."
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
    path = Path(path)
    if fmt.kind == "TEXT":
        parsed = parse_text_gcode(path)
        return parsed, parsed, None

    if fmt.kind == "BINARY":
        native = parse_binary_gcode(path)
        converted = _convert_bgcode_to_text(path)
        temp_dir = converted.parent
        text_parsed = parse_text_gcode(converted)
        return native, text_parsed, temp_dir

    raise ValidationError(f"Unsupported detected format {fmt.kind!r}.")
