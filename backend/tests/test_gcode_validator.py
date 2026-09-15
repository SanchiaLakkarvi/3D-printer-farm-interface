from __future__ import annotations

from pathlib import Path

import pytest

from app.services.gcode_parser import ParsedGCode
from app.services.gcode_validator import validate_upload

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "gcode"


def test_valid_coreone_fixture_passes() -> None:
    result = validate_upload(FIXTURES / "valid_coreone.gcode")
    assert result["status"] == "PASS"
    assert result["passed"] is True
    assert result["compatible_profile"] == "core_one_hf04"
    assert result["compatible_printer"] == "Prusa CORE One HF0.4 nozzle"


def test_wrong_printer_fixture_fails_profile_match() -> None:
    result = validate_upload(FIXTURES / "wrong_printer.gcode")
    assert result["status"] == "FAIL"
    assert result["failed_stage"] in {4, 6}
    assert result["compatible_profiles"] == []


def test_missing_metadata_fixture_fails_stage_3() -> None:
    result = validate_upload(FIXTURES / "missing_metadata.gcode")
    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 3
    assert "filament_type" in result["errors"][0]


def test_binary_rejected_fixture_fails_stage_1() -> None:
    result = validate_upload(FIXTURES / "binary_rejected.gcode")
    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 1


def test_bgcode_missing_converter_reports_clear_dependency_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    bgcode_path = tmp_path / "sample.bgcode"
    bgcode_path.write_bytes(b"GCDE\x01\x00\x00\x00")

    monkeypatch.setattr("app.services.gcode_parser.shutil.which", lambda *_args, **_kwargs: None)

    from app.services import gcode_parser

    monkeypatch.setattr(gcode_parser, "parse_binary_gcode", lambda _path: ParsedGCode(
        kind="BINARY",
        file_metadata={},
        printer_metadata={},
        print_metadata={},
        slicer_metadata={},
        gcode_blocks=1,
        integrity_ok=True,
    ))

    result = validate_upload(bgcode_path)
    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 2
    assert "bgcode" in result["errors"][0].lower()
