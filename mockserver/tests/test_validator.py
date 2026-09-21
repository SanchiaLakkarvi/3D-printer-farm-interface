from pathlib import Path

import pybgcode
import pytest

from app.config import load_config
from app.models import AppConfig
from app.validator import GCodeValidator

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "printers.yaml"


def configured(printer_id: str):
    config = load_config(str(CONFIG))
    printer = next(item for item in config.printers if item.id == printer_id)
    profile = next(
        item
        for item in config.approved_profiles
        if item.id == printer.approved_profile_id
    )
    return config, printer, profile


def validate_fixture(filename: str, printer_id: str):
    config, printer, profile = configured(printer_id)
    result = GCodeValidator(config.gcode_tail_bytes).validate(
        str(ROOT / "tests" / filename), printer, profile
    )
    return result


def test_valid_xl5is_ascii_gcode():
    result = validate_fixture("data-valid-xl.gcode", "mock-xl-01")

    assert result.valid
    assert result.file_format == "ascii"
    assert result.used_tools == [0]
    assert result.metrics["estimated_print_duration"] == 600
    assert result.metrics["estimated_filament_weight"] == [3.58, 0, 0, 0, 0]


def test_valid_coreone_hf_ascii_gcode():
    result = validate_fixture("data-valid-coreone.gcode", "mock-coreone-01")

    assert result.valid
    assert result.used_tools == [0]
    assert result.metadata["printer_model"] == "COREONE"


def test_wrong_printer_is_rejected():
    result = validate_fixture("data-invalid-wrong-printer.gcode", "mock-xl-01")

    assert not result.valid
    rule_ids = {issue.rule_id for issue in result.issues}
    assert "printer-model" in rule_ids
    assert "firmware-model-command" in rule_ids


def test_coreone_requires_high_flow_command(tmp_path: Path):
    source = (ROOT / "tests" / "data-valid-coreone.gcode").read_text()
    path = tmp_path / "wrong-flow.gcode"
    path.write_text(source.replace("M862.1 P0.4 A0 F1", "M862.1 P0.4 A0 F0"))
    config, printer, profile = configured("mock-coreone-01")

    result = GCodeValidator(config.gcode_tail_bytes).validate(str(path), printer, profile)

    assert not result.valid
    assert any(issue.rule_id == "nozzle-command-mismatch" for issue in result.issues)


def test_unsafe_commands_are_rejected(tmp_path: Path):
    source = (ROOT / "tests" / "data-valid-coreone.gcode").read_text()
    unsafe = source.replace(
        "; prusaslicer_config = begin",
        "G1 X251\nM104 S291\nM141 S56\nM997\n; prusaslicer_config = begin",
    )
    path = tmp_path / "unsafe.gcode"
    path.write_text(unsafe)
    config, printer, profile = configured("mock-coreone-01")

    result = GCodeValidator(config.gcode_tail_bytes).validate(str(path), printer, profile)

    rule_ids = {issue.rule_id for issue in result.issues}
    assert {
        "motion-bound-x",
        "nozzle-temperature-limit",
        "chamber-temperature-limit",
        "forbidden-command",
    } <= rule_ids


def test_invalid_coreone_hardware_config_is_rejected():
    config = load_config(str(CONFIG)).model_dump()
    core = next(item for item in config["printers"] if item["id"] == "mock-coreone-01")
    core["toolheads"][0]["high_flow"] = False

    with pytest.raises(ValueError, match="high-flow 0.4 mm"):
        AppConfig.model_validate(config)


def test_valid_xl_binary_gcode(tmp_path: Path):
    binary_path = tmp_path / "valid-xl.bgcode"
    source = pybgcode.open(str(ROOT / "tests" / "data-valid-xl.gcode"), "rb")
    output = pybgcode.open(str(binary_path), "wb")
    try:
        conversion = pybgcode.from_ascii_to_binary(
            source, output, pybgcode.get_config()
        )
    finally:
        pybgcode.close(source)
        pybgcode.close(output)
    assert conversion == pybgcode.EResult.Success

    config, printer, profile = configured("mock-xl-01")
    result = GCodeValidator(config.gcode_tail_bytes).validate(
        str(binary_path), printer, profile
    )

    assert result.valid
    assert result.file_format == "binary"
    assert result.metadata["printer_model"] == "XL5IS"
