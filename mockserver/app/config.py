from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import AppConfig


def load_config(path: str | None = None) -> AppConfig:
    config_path = Path(path or os.environ.get("MOCK_PRINTER_CONFIG", "config/printers.yaml"))
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    # Optional demo override; validate the value through PrinterConfig as usual.
    speed = os.environ.get("MOCK_SIMULATION_SPEED")
    if speed is not None:
        for printer in raw["printers"]:
            printer["simulation_speed"] = float(speed)
    return AppConfig.model_validate(raw)
