"""CLI script to seed demo printers and materials for local/dev use.

Run: python -m app.scripts.seed_printers
Requires: .env loaded, migrations applied.
"""

from __future__ import annotations

import uuid
import sys

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import PrinterStatus
from app.models.material import Material
from app.models.printer import Printer


DEMO_MATERIALS = [
    {"name": "PLA Black", "type": "PLA", "colour": "black"},
    {"name": "PLA White", "type": "PLA", "colour": "white"},
    {"name": "PETG Blue", "type": "PETG", "colour": "blue"},
]

DEMO_PRINTERS = [
    {
        "model": "Prusa CORE One",
        "bed_size": "250x210",
        "location": "Lab A — Bench 1",
        "status": PrinterStatus.IDLE,
    },
    {
        "model": "Prusa CORE One",
        "bed_size": "250x210",
        "location": "Lab A — Bench 2",
        "status": PrinterStatus.IDLE,
    },
    {
        "model": "Prusa XL",
        "bed_size": "360x360",
        "location": "Lab B — Large Format",
        "status": PrinterStatus.IDLE,
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

    for i, p in enumerate(DEMO_PRINTERS):
        printer = Printer(
            id=uuid.uuid4(),
            current_material_id=materials[i % len(materials)].id,
            **p,
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
