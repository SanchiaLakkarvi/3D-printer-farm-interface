"""CLI script to seed demo printers and materials for local/dev use.

Run: python -m app.scripts.seed_printers
Requires: .env loaded, migrations applied. Printers point at
MOCK_PRINTER_BASE_URL (the mock server) using its synthetic credentials.
"""

from __future__ import annotations

import uuid
import sys

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.enums import PrinterStatus
from app.models.material import Material
from app.models.printer import Printer


DEMO_MATERIALS = [
    {"name": "PLA Black", "type": "PLA", "colour": "black"},
    {"name": "PLA White", "type": "PLA", "colour": "white"},
    {"name": "PETG Blue", "type": "PETG", "colour": "blue"},
]

# Each demo printer maps to a mock printer served by mockserver/ (see its README).
# ``validator_profile`` links it to a profile in app.validation.gcode_validator.
DEMO_PRINTERS = [
    {
        "model": "Prusa CORE One",
        "bed_size": "250x220",
        "location": "Lab A — Bench 1",
        "status": PrinterStatus.IDLE,
        "locked_profile": {"validator_profile": "core_one_hf04"},
        "mock_id": "mock-coreone-01",
        "mock_token": "mock-core-token",
    },
    {
        "model": "Prusa XL",
        "bed_size": "360x360",
        "location": "Lab B — Large Format",
        "status": PrinterStatus.IDLE,
        "locked_profile": {"validator_profile": "xl_5t_is_04"},
        "mock_id": "mock-xl-01",
        "mock_token": "mock-xl-token",
    },
]


def seed(db: Session) -> None:
    """Insert demo materials and printers if tables are empty."""
    if db.query(Material).count() > 0:
        print("Materials table not empty — skipping seed.")
        return

    materials = []
    for m in DEMO_MATERIALS:
        material = Material(id=uuid.uuid4(), **m)
        db.add(material)
        materials.append(material)
    db.flush()
    print(f"Seeded {len(materials)} materials.")

    for i, spec in enumerate(DEMO_PRINTERS):
        spec = dict(spec)
        mock_id = spec.pop("mock_id")
        token = spec.pop("mock_token")
        printer = Printer(
            id=uuid.uuid4(),
            current_material_id=materials[i % len(materials)].id,
            prusalink_url=f"{settings.mock_printer_base_url.rstrip('/')}/prusalink/{mock_id}",
            prusalink_username="maker",
            prusalink_password=token,
            **spec,
        )
        db.add(printer)
    db.commit()
    print(f"Seeded {len(DEMO_PRINTERS)} printers.")


if __name__ == "__main__":
    session = SessionLocal()
    try:
        seed(session)
    except Exception as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        session.rollback()
        raise
    finally:
        session.close()
