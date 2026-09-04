"""CLI: seed demo Admin + Farmers into Auth and application profiles.

Usage (from backend/, with .env passwords set):

    python -m app.scripts.seed_users

Does not commit secrets. Uses AUTH_ADAPTER (fake or supabase) + DATABASE_URL.
"""

from __future__ import annotations

from app.api.deps import get_auth_port
from app.core.config import settings
from app.db.session import SessionLocal
from app.services import auth_service


def main() -> None:
    db = SessionLocal()
    try:
        auth = get_auth_port()
        users = auth_service.seed_demo_users(db=db, auth=auth, settings=settings)
        summary = [(user.email, user.role.value, str(user.id)) for user in users]
    finally:
        db.close()

    print(f"Seeded {len(summary)} Seed Users:")
    for email, role, user_id in summary:
        print(f"  - {email} ({role}) id={user_id}")


if __name__ == "__main__":
    main()
