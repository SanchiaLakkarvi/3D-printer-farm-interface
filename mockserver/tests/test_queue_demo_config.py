from pathlib import Path
import importlib.util

import pytest
from pydantic import ValidationError

from app.config import load_config

CONFIG = Path(__file__).resolve().parents[1] / "config/printers.yaml"


def test_demo_uses_wall_clock_speed(monkeypatch):
    monkeypatch.setenv("MOCK_SIMULATION_SPEED", "1")
    assert all(p.simulation_speed == 1 for p in load_config(str(CONFIG)).printers)


def test_invalid_speed_is_rejected(monkeypatch):
    monkeypatch.setenv("MOCK_SIMULATION_SPEED", "0")
    with pytest.raises(ValidationError):
        load_config(str(CONFIG))


def test_queue_demo_file_passes_mock_validation(tmp_path):
    from app.validator import GCodeValidator

    runner = CONFIG.parents[2] / "backend/app/scripts/queue_demo.py"
    spec = importlib.util.spec_from_file_location("queue_demo", runner)
    demo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(demo)
    path = tmp_path / "queue-demo.gcode"
    path.write_bytes(demo.demo_gcode())
    config = load_config(str(CONFIG))
    printer = next(p for p in config.printers if p.id == "mock-coreone-01")
    profile = next(p for p in config.approved_profiles if p.id == printer.approved_profile_id)
    result = GCodeValidator(config.gcode_tail_bytes).validate(str(path), printer, profile)
    assert result.valid, result.issues
    assert result.metrics["estimated_print_duration"] == 210
