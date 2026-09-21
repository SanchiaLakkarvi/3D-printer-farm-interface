from pathlib import Path

import pytest
from prusa.connect.printer import const

from app.config import load_config
from app.transport import LegacySdkMockTransport

ROOT = Path(__file__).resolve().parents[1]


def xl_config(tmp_path: Path):
    config = load_config(str(ROOT / "config" / "printers.yaml"))
    printer = next(item for item in config.printers if item.id == "mock-xl-01")
    printer.storage_dir = str(tmp_path)
    return printer


def test_legacy_mock_transport_registers_bgcode_as_print_file(tmp_path: Path):
    LegacySdkMockTransport(xl_config(tmp_path), "http://127.0.0.1:9000")

    assert ".bgcode" in const.GCODE_EXTENSIONS


def test_legacy_transport_rejects_non_mock_identity(tmp_path: Path):
    printer = xl_config(tmp_path)
    printer.sdk_identity.header = "XL"

    with pytest.raises(ValueError, match="synthetic MOCK identity"):
        LegacySdkMockTransport(printer, "http://127.0.0.1:9000")
