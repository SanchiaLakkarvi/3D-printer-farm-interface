from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gcode_validator import validate_upload

SAMPLE = ROOT / "samples" / "Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.bgcode"


def _write_text_gcode(path: Path, metadata: dict[str, str]) -> None:
    lines = [
        "; generated test fixture",
        "G28 ; home",
        "G1 X10 Y10 Z0.2 F1200",
        "M104 S210",
        "; bottom metadata begins",
    ]
    for key, value in metadata.items():
        lines.append(f"; {key} = {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_real_uploaded_gcode_checks_both_and_matches_core_one():
    result = validate_upload(SAMPLE)

    assert result["status"] == "PASS"
    assert result["format"] == "GCODE"
    assert [s["status"] for s in result["validation_stages"]] == [
        "PASS", "PASS", "PASS", "PASS", "PASS"
    ]

    assert set(result["printer_checks"]) == {"core_one_hf04", "xl_5t_is_04"}
    assert result["printer_checks"]["core_one_hf04"]["result"] == "MATCH"
    assert result["printer_checks"]["xl_5t_is_04"]["result"] == "NO_MATCH"
    assert result["compatible_profile"] == "core_one_hf04"
    assert result["next_step"] == "SELECT_PRINTER"


def test_wrong_format_fails_stage_1(tmp_path: Path):
    fake = tmp_path / "photo.bgcode"
    fake.write_bytes(b"not a real binary gcode file")

    result = validate_upload(fake)

    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 1
    assert result["next_step"] == "UPLOAD_GCODE"
    assert all(x["result"] == "NOT_CHECKED" for x in result["printer_checks"].values())


def test_extension_content_mismatch_fails_stage_1(tmp_path: Path):
    wrong_name = tmp_path / "binary.gcode"
    wrong_name.write_bytes(SAMPLE.read_bytes())

    result = validate_upload(wrong_name)

    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 1
    assert "extension does not match" in result["errors"][0]


def test_corrupted_gcode_fails_stage_2(tmp_path: Path):
    data = bytearray(SAMPLE.read_bytes())
    # Change data near the end without updating the owning block's CRC.
    data[-20] ^= 0x01
    broken = tmp_path / "broken.bgcode"
    broken.write_bytes(data)

    result = validate_upload(broken)

    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 2
    assert any("CRC32" in msg for msg in result["errors"])
    assert result["next_step"] == "UPLOAD_GCODE"


def test_text_gcode_matches_xl_5t_profile(tmp_path: Path):
    xl = tmp_path / "xl.gcode"
    _write_text_gcode(
        xl,
        {
            "printer_model": "XL5IS",
            "printer_variant": "0.4",
            "printer_settings_id": "Original Prusa XL - 5T Input Shaper 0.4 nozzle",
            "nozzle_diameter": "0.4,0.4,0.4,0.4,0.4",
            "filament_type": "PLA;PLA;PLA;PLA;PLA",
            "layer_height": "0.20",
        },
    )

    result = validate_upload(xl)

    assert result["status"] == "PASS"
    assert result["format"] == "GCODE"
    assert result["printer_checks"]["core_one_hf04"]["result"] == "NO_MATCH"
    assert result["printer_checks"]["xl_5t_is_04"]["result"] == "MATCH"
    assert result["compatible_profile"] == "xl_5t_is_04"
    assert result["next_step"] == "SELECT_PRINTER"


def test_text_gcode_matches_core_one_hf04_profile(tmp_path: Path):
    core = tmp_path / "core.gcode"
    _write_text_gcode(
        core,
        {
            "printer_model": "COREONE",
            "printer_variant": "HF0.4",
            "printer_settings_id": "Prusa CORE One HF0.4 nozzle",
            "nozzle_diameter": "0.4",
            "nozzle_high_flow": "1",
            "filament_type": "PLA",
            "layer_height": "0.15",
        },
    )

    result = validate_upload(core)

    assert result["status"] == "PASS"
    assert result["printer_checks"]["core_one_hf04"]["result"] == "MATCH"
    assert result["printer_checks"]["xl_5t_is_04"]["result"] == "NO_MATCH"


def test_valid_gcode_but_neither_printer_matches_fails_stage_5(tmp_path: Path):
    other = tmp_path / "other.gcode"
    _write_text_gcode(
        other,
        {
            "printer_model": "MK4S",
            "printer_variant": "0.4",
            "printer_settings_id": "Another supported-by-slicer printer",
            "nozzle_diameter": "0.4",
        },
    )

    result = validate_upload(other)

    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 5
    assert result["printer_checks"]["core_one_hf04"]["result"] == "NO_MATCH"
    assert result["printer_checks"]["xl_5t_is_04"]["result"] == "NO_MATCH"
    assert result["next_step"] == "UPLOAD_GCODE"


def test_missing_printer_metadata_fails_stage_3(tmp_path: Path):
    missing = tmp_path / "missing.gcode"
    missing.write_text("G28\nG1 X10 Y10\n; layer_height = 0.2\n", encoding="utf-8")

    result = validate_upload(missing)

    assert result["status"] == "FAIL"
    assert result["failed_stage"] == 3
    assert result["next_step"] == "UPLOAD_GCODE"

