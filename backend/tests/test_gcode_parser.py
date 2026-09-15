from __future__ import annotations

from pathlib import Path

import pytest

from app.services.gcode_parser import parse_text_gcode, validate_file_format

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcode"


def test_validate_file_format_accepts_valid_text_fixture() -> None:
    result = validate_file_format(FIXTURES / "valid_coreone.gcode")
    assert result.kind == "TEXT"
    assert result.extension == ".gcode"


def test_validate_file_format_rejects_binary_nul_text_fixture() -> None:
    with pytest.raises(ValueError, match="binary|NUL|not valid text"):
        validate_file_format(FIXTURES / "binary_rejected.gcode")


def test_parse_text_gcode_reads_coreone_metadata() -> None:
    parsed = parse_text_gcode(FIXTURES / "valid_coreone.gcode")
    assert parsed.kind == "TEXT"
    assert parsed.integrity_ok is True
    assert parsed.config_complete is True
    assert parsed.gcode_blocks > 0
    assert parsed.printer_metadata["printer_model"] == "COREONE"
    assert parsed.printer_metadata["filament_type"] == "PLA"
