"""Submit department demo jobs through the normal API; never command printers."""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import httpx

ACCOUNTS = [
    ("90000001@student.uwa.edu.au", "Engineering"),
    ("90000002@student.uwa.edu.au", "Architecture"),
    ("90000003@student.uwa.edu.au", "Science"),
]
SAMPLE = Path(__file__).resolve().parents[1] / "validation/data/Rook1_0.4n_0.15mm_PLA_COREONE_1h5m.gcode"


def demo_gcode() -> bytes:
    """Modify only this in-memory mock fixture, leaving the source file intact."""
    data, changes = re.subn(
        rb"(?m)^; estimated printing time \(normal mode\) = [^\r\n]+",
        b"; estimated printing time (normal mode) = 3m 30s",
        SAMPLE.read_bytes(),
    )
    if changes == 0:
        raise ValueError("Missing duration field in the demo G-code")
    return data


def checked(response: httpx.Response):
    response.raise_for_status()
    return response.json()


def submit(client, email: str, department: str, sequence: int, data: bytes):
    session = checked(client.post("/api/auth/signin", json={
        "email": email, "password": "demo-password-1",
    }))
    headers = {"Authorization": f"Bearer {session['access_token']}"}
    printers = checked(client.get("/api/printers", headers=headers))
    matches = [p for p in printers if p["model"] == "Prusa CORE One"
               and p["location"].startswith("Lab A")]
    if len(matches) != 1:
        raise ValueError("Expected exactly one seeded CORE One demo printer")
    printer = matches[0]
    material = printer.get("current_material")
    if not material or material["type"].upper() != "PLA":
        raise ValueError("Demo CORE One must have PLA loaded")
    return checked(client.post("/api/jobs", headers=headers,
        data={"printer_id": printer["id"], "material_id": material["id"]},
        files={"file": (f"queue-demo-{sequence:03d}-{department}.gcode", data, "text/plain")},
    ))


def run(client, count: int, interval: float, *, sleep=time.sleep, clock=time.monotonic):
    data = demo_gcode()
    due = clock()
    for index in range(count):
        sleep(max(0, due - clock()))
        email, department = ACCOUNTS[index % len(ACCOUNTS)]
        job = submit(client, email, department, index + 1, data)
        print(f"{index + 1}/{count}: {department}: {job['job_id']} ({job['status']})", flush=True)
        # Avoid bursts of catch-up submissions after a slow request.
        due = max(due + interval, clock())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--interval", type=float, default=180)
    args = parser.parse_args()
    if args.count < 1 or args.interval <= 0:
        parser.error("count and interval must be positive")
    with httpx.Client(base_url=args.base_url, timeout=60) as client:
        for attempt in range(60):
            try:
                response = client.get("/health")
                response.raise_for_status()
                break
            except httpx.HTTPError:
                if attempt == 59:
                    raise RuntimeError("Backend did not become ready") from None
                time.sleep(2)
        try:
            run(client, args.count, args.interval)
        except KeyboardInterrupt:
            print("Stopped submitting; existing jobs remain in the queue.")


if __name__ == "__main__":
    main()
