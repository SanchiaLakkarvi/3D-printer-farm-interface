from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_ASSIGNMENT = re.compile(r"^\s*;\s*([^=]+?)\s*=\s*(.*?)\s*$")
_BGCODE_MAGIC = b"GCDE"


@dataclass(frozen=True)
class GCodeDocument:
    format: Literal["ascii", "binary"]
    metadata: dict[str, str]
    commands: str


def normalize_key(key: str) -> str:
    return " ".join(key.strip().lower().split())


def read_tail(path: str | Path, max_bytes: int) -> str:
    file_path = Path(path)
    size = file_path.stat().st_size
    if size == 0:
        raise ValueError("G-code file is empty")
    with file_path.open("rb") as handle:
        handle.seek(max(0, size - max_bytes))
        data = handle.read()
    return data.decode("utf-8", errors="replace")


def parse_tail_metadata(path: str | Path, max_bytes: int) -> dict[str, str]:
    """Parse PrusaSlicer-style comment assignments from the file tail.

    The parser intentionally does not assume a fixed list of PrusaSlicer keys.
    It captures every `; key = value` assignment and lets the approved profile
    decide which exact keys are mandatory. If a key appears multiple times, the
    last occurrence wins, matching the requirement to inspect the final config.
    """
    return parse_metadata_text(read_tail(path, max_bytes))


def parse_metadata_text(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in text.splitlines():
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        key, value = match.groups()
        metadata[normalize_key(key)] = value.strip()
    return metadata


def parse_gcode_document(path: str | Path, max_bytes: int) -> GCodeDocument:
    file_path = Path(path)
    with file_path.open("rb") as handle:
        magic = handle.read(4)
    if magic == _BGCODE_MAGIC:
        return _parse_binary_document(file_path)
    commands = file_path.read_text(encoding="utf-8", errors="replace")
    return GCodeDocument(
        format="ascii",
        metadata=parse_metadata_text(commands[-max_bytes:]),
        commands=commands,
    )


def _parse_binary_document(path: Path) -> GCodeDocument:
    try:
        import pybgcode  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError(
            "Binary G-code requires the official pybgcode dependency"
        ) from exc

    source = pybgcode.open(str(path), "rb")
    try:
        metadata: dict[str, str] = {}
        for block_type in ("file", "printer", "print", "slicer"):
            block = pybgcode.read_metadata(source, block_type) or {}
            metadata.update(
                {normalize_key(str(key)): str(value) for key, value in block.items()}
            )

        with tempfile.TemporaryDirectory(prefix="prusa-bgcode-") as directory:
            ascii_path = Path(directory) / "decoded.gcode"
            output = pybgcode.open(str(ascii_path), "wb")
            try:
                pybgcode.rewind(source)
                result = pybgcode.from_binary_to_ascii(source, output, True)
                if result != pybgcode.EResult.Success:
                    raise ValueError(
                        f"Cannot decode Binary G-code: {pybgcode.translate_result(result)}"
                    )
            finally:
                pybgcode.close(output)
            commands = ascii_path.read_text(encoding="utf-8", errors="strict")
    finally:
        pybgcode.close(source)

    return GCodeDocument(format="binary", metadata=metadata, commands=commands)


def parse_number(value: str) -> float:
    match = re.search(r"[-+]?\d+(?:\.\d+)?", value.replace(",", "."))
    if not match:
        raise ValueError(f"No numeric value in {value!r}")
    return float(match.group(0))


def parse_number_sequence(value: str) -> list[float]:
    return [parse_number(part) for part in split_sequence(value)]


def parse_duration_seconds(value: str) -> float:
    """Parse strings such as `1d 2h 3m 4s`, `2h 10m`, or plain seconds."""
    stripped = value.strip().lower()
    if re.fullmatch(r"[-+]?\d+(?:\.\d+)?", stripped):
        return float(stripped)
    parts = re.findall(r"(\d+(?:\.\d+)?)\s*([dhms])", stripped)
    if not parts:
        raise ValueError(f"Cannot parse duration: {value!r}")
    multipliers = {"d": 86400.0, "h": 3600.0, "m": 60.0, "s": 1.0}
    return sum(float(number) * multipliers[unit] for number, unit in parts)


def split_sequence(value: str) -> list[str]:
    return [
        part.strip().strip('"')
        for part in re.split(r"[;,]", value)
        if part.strip().strip('"')
    ]
