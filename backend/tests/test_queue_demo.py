"""Exercise demo submissions through real validation, auth and queue endpoints."""
from sqlalchemy import select

from app.models.enums import JobStatus
from app.models.print_job import PrintJob
from app.scripts.queue_demo import ACCOUNTS, run
from app.services.demo_accounts import parse_demo_accounts, seed_demo_accounts
from tests.test_submission import env  # noqa: F401 -- shared seeded printer/material fixture


def test_demo_rotates_departments_and_queues_every_three_minutes(env, auth_adapter):
    db, client = env["db"], env["client"]
    printer = env["core_one"]
    printer.current_material_id = env["pla"].id
    db.commit()
    accounts = ",".join(f"{email}:demo-password-1:student:{dept}" for email, dept in ACCOUNTS)
    accounts += ",00000001@student.uwa.edu.au:demo-password-1:admin"
    seed_demo_accounts(db, auth_adapter, parse_demo_accounts(accounts))
    now = [0.0]
    delays = []

    def sleep(seconds):
        delays.append(seconds)
        now[0] += seconds

    run(client, 4, 180, sleep=sleep, clock=lambda: now[0])
    assert delays == [0, 180, 180, 180]
    jobs = list(db.scalars(select(PrintJob).order_by(PrintJob.submitted_at)))
    assert [j.department for j in jobs] == ["Engineering", "Architecture", "Science", "Engineering"]
    assert all(j.status is JobStatus.QUEUED and j.est_duration_min == 3.5 for j in jobs)
    assert all(j.printer_id == printer.id for j in jobs)
    token = client.post("/api/auth/signin", json={
        "email": "00000001@student.uwa.edu.au", "password": "demo-password-1",
    }).json()["access_token"]
    queue = client.get("/api/jobs/queue", headers={"Authorization": f"Bearer {token}"}).json()
    assert [j["department"] for j in queue] == [j.department for j in jobs]
    assert all(j["est_duration_formatted"] == "3m 30s" for j in queue)
    # Restarting fake auth reuses the same profiles and retains their departments.
    from app.adapters.auth.fake import FakeAuthAdapter
    from app.models.user import User
    seed_demo_accounts(db, FakeAuthAdapter(), parse_demo_accounts(accounts))
    assert len(list(db.scalars(select(User).where(User.email.in_([a[0] for a in ACCOUNTS]))))) == 3
